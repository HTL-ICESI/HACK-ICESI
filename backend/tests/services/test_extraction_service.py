"""
Tests del orquestador M2 (ExtractionService).

Verifican la frontera anti-alucinación:
- todo campo numérico OK trae `source` (cita);
- un campo blando que el LLM afirma SIN span verificable -> `needs_human`;
- un campo blando que el LLM ni menciona -> `not_found` (no se inventa);
- un campo blando con span válido -> `ok` con su `source`.
"""
import pytest

from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.adapters.storage.repository import InMemoryRepository
from app.domain.models import FieldStatus
from app.services.extraction_service import ExtractionService

CTX = TenantContext(tenant_id="empresa-001")

# Nota: usamos "El puesto de Asesor comercial" (no "cargo de") a propósito, para que
# role NO lo capture el extractor determinista y estos tests ejerciten la ruta del LLM
# (validación de span de campos blandos). La extracción determinista de role/employer
# se prueba aparte en los tests de dominio.
CONTRATO = (
    "CONTRATO DE TRABAJO. El puesto de Asesor comercial sera ejercido por el "
    "trabajador. El contrato regira a partir del 1 de febrero de 2024 hasta el "
    "31 de enero de 2025. Cumplira una jornada de cuarenta y ocho horas "
    "semanales. El salario mensual: 2.500.000 pesos m/cte."
)


class FakeClaude:
    """Doble de prueba del adapter LLM: devuelve lo que se le configure."""
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def extract_soft_fields(self, text: str, schema: dict) -> dict:
        return self._payload


def _service(payload: dict) -> ExtractionService:
    return ExtractionService(InMemoryRepository(), AuditLog(), FakeClaude(payload))


@pytest.mark.asyncio
async def test_campos_numericos_siempre_traen_source():
    svc = _service({})
    rec = await svc.extract(CTX, "contrato-001", CONTRATO)

    # El salario salio del regex determinista, con cita.
    assert rec.base_salary.status == FieldStatus.OK
    assert rec.base_salary.value.value == 2500000.0
    assert rec.base_salary.source is not None
    # Toda fecha/jornada OK trae span no nulo (ningun numero "afirmado" sin fuente).
    for field in (rec.start_date, rec.end_date, rec.weekly_hours):
        assert field.status == FieldStatus.OK
        assert field.source is not None
    assert rec.start_date.value == "2024-02-01"
    assert rec.weekly_hours.value == 48


@pytest.mark.asyncio
async def test_campo_blando_sin_span_va_a_needs_human():
    # El LLM afirma un cargo pero NO entrega span -> no se afirma: needs_human.
    svc = _service({"role": {"value": "Gerente inventado"}})
    rec = await svc.extract(CTX, "c2", CONTRATO)

    assert rec.role.status == FieldStatus.NEEDS_HUMAN
    assert rec.role.source is None
    assert rec.role.value == "Gerente inventado"  # candidato, marcado para revisión


@pytest.mark.asyncio
async def test_campo_blando_con_span_valido_queda_ok():
    start = CONTRATO.index("Asesor comercial")
    end = start + len("Asesor comercial")
    svc = _service({"role": {"value": "Asesor comercial",
                             "span_start": start, "span_end": end, "confidence": 0.92}})
    rec = await svc.extract(CTX, "c3", CONTRATO)

    assert rec.role.status == FieldStatus.OK
    assert rec.role.source is not None
    assert rec.role.source.text == "Asesor comercial"
    assert rec.role.value == "Asesor comercial"


@pytest.mark.asyncio
async def test_campo_blando_no_mencionado_es_not_found():
    # El LLM no devuelve 'employer' -> not_found, sin valor inventado.
    svc = _service({})
    rec = await svc.extract(CTX, "c4", CONTRATO)

    assert rec.employer.status == FieldStatus.NOT_FOUND
    assert rec.employer.value is None
    assert rec.employer.source is None


@pytest.mark.asyncio
async def test_span_fuera_de_rango_se_rechaza_y_va_a_needs_human():
    # Un span que no corresponde al texto no es cita valida -> needs_human.
    svc = _service({"vinculo_type": {"value": "termino_fijo",
                                     "span_start": 9000, "span_end": 9010}})
    rec = await svc.extract(CTX, "c5", CONTRATO)

    assert rec.vinculo_type.status == FieldStatus.NEEDS_HUMAN
    assert rec.vinculo_type.source is None


@pytest.mark.asyncio
async def test_record_se_persiste_namespaced_por_tenant():
    repo = InMemoryRepository()
    svc = ExtractionService(repo, AuditLog(), FakeClaude({}))
    rec = await svc.extract(CTX, "c6", CONTRATO)
    assert repo.get(CTX, "records", "c6") is rec


# ---------------------------------------------------------------------------
# Nuevos casos: bordes de validación de span
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_span_inicio_igual_fin_rechazado():
    # span_start == span_end → span de longitud 0 → inválido → needs_human.
    svc = _service({"role": {"value": "Gerente", "span_start": 10, "span_end": 10}})
    rec = await svc.extract(CTX, "c7", CONTRATO)

    assert rec.role.status == FieldStatus.NEEDS_HUMAN
    assert rec.role.source is None


@pytest.mark.asyncio
async def test_span_invertido_rechazado():
    # span_start > span_end → span invertido → inválido → needs_human.
    svc = _service({"role": {"value": "Analista", "span_start": 50, "span_end": 20}})
    rec = await svc.extract(CTX, "c8", CONTRATO)

    assert rec.role.status == FieldStatus.NEEDS_HUMAN
    assert rec.role.source is None


@pytest.mark.asyncio
async def test_span_solo_espacios_rechazado():
    # Span que apunta solo a espacios → snippet.strip() vacío → needs_human.
    # Encontramos un segmento de solo espacio en CONTRATO.
    space_idx = CONTRATO.index(" ")
    svc = _service({"role": {"value": "Coordinador",
                              "span_start": space_idx,
                              "span_end": space_idx + 1}})
    rec = await svc.extract(CTX, "c9", CONTRATO)

    assert rec.role.status == FieldStatus.NEEDS_HUMAN
    assert rec.role.source is None


# ---------------------------------------------------------------------------
# Degradación honesta: LLM lanza excepción → campos blandos a not_found
# ---------------------------------------------------------------------------

class _FailingClaude:
    async def extract_soft_fields(self, text: str, schema: dict) -> dict:
        raise RuntimeError("API unavailable")


@pytest.mark.asyncio
async def test_span_llm_incorrecto_valor_en_texto_se_corrige():
    # El LLM da el valor correcto pero un span apuntando al lugar equivocado.
    # El service debe encontrar el valor en el texto y usar el span real.
    wrong_start = CONTRATO.index("CONTRATO")          # span del título, no del cargo
    wrong_end = wrong_start + 8
    svc = _service({"role": {"value": "Asesor comercial",
                             "span_start": wrong_start, "span_end": wrong_end}})
    rec = await svc.extract(CTX, "c-fix", CONTRATO)

    assert rec.role.status == FieldStatus.OK
    assert rec.role.value == "Asesor comercial"
    # El span corregido debe apuntar al texto real, no al título.
    assert rec.role.source is not None
    assert "Asesor comercial" in rec.role.source.text
    # La confidence viene del LLM (no dimos una → default 0.85).
    assert rec.role.source.confidence == 0.85


@pytest.mark.asyncio
async def test_valor_no_en_texto_va_a_needs_human():
    # El LLM afirma un valor que NO aparece en el texto → no se puede verificar.
    svc = _service({"role": {"value": "Gerente inventado",
                             "span_start": 0, "span_end": 10}})
    rec = await svc.extract(CTX, "c-fake", CONTRATO)

    assert rec.role.status == FieldStatus.NEEDS_HUMAN
    assert rec.role.source is None


@pytest.mark.asyncio
async def test_vinculo_type_enum_se_localiza_en_texto():
    # El LLM devuelve el enum 'termino_fijo' con span incorrecto.
    # El service debe encontrar "termino fijo" en el texto y corregir el span.
    svc = _service({"vinculo_type": {"value": "termino_fijo",
                                     "span_start": 9000, "span_end": 9010}})
    # CONTRATO contiene "CONTRATO DE TRABAJO. El cargo..." → no tiene "termino fijo".
    # Esperamos needs_human porque el valor no aparece en CONTRATO.
    rec = await svc.extract(CTX, "c-enum", CONTRATO)
    # CONTRATO no dice "termino fijo" → no se puede localizar → needs_human.
    assert rec.vinculo_type.status == FieldStatus.NEEDS_HUMAN


@pytest.mark.asyncio
async def test_blando_valor_string_vacio_es_not_found():
    # El LLM devuelve value="" (cadena vacía) → equivale a no encontrado.
    svc = _service({"role": {"value": "", "span_start": 10, "span_end": 20}})
    rec = await svc.extract(CTX, "c11", CONTRATO)

    assert rec.role.status == FieldStatus.NOT_FOUND
    assert rec.role.value is None


@pytest.mark.asyncio
async def test_dos_extracciones_mismo_tenant_distintos_docs():
    repo = InMemoryRepository()
    svc = ExtractionService(repo, AuditLog(), FakeClaude({}))

    rec_a = await svc.extract(CTX, "doc-alpha", CONTRATO)
    rec_b = await svc.extract(CTX, "doc-beta", CONTRATO)

    # Cada doc_id tiene su propio record independiente en el repo.
    assert repo.get(CTX, "records", "doc-alpha") is rec_a
    assert repo.get(CTX, "records", "doc-beta") is rec_b
    assert rec_a is not rec_b


@pytest.mark.asyncio
async def test_source_doc_id_coincide_con_el_del_request():
    svc = _service({})
    rec = await svc.extract(CTX, "mi-contrato-xyz", CONTRATO)

    # Cada source numérico lleva el doc_id del request, no un valor genérico.
    assert rec.base_salary.source.doc_id == "mi-contrato-xyz"
    assert rec.start_date.source.doc_id == "mi-contrato-xyz"
    assert rec.weekly_hours.source.doc_id == "mi-contrato-xyz"


@pytest.mark.asyncio
async def test_llm_excepcion_degrada_campos_blandos_a_not_found():
    svc = ExtractionService(InMemoryRepository(), AuditLog(), _FailingClaude())
    rec = await svc.extract(CTX, "c10", CONTRATO)

    # Los campos duros (regex) siguen ok a pesar del fallo del LLM.
    assert rec.base_salary.status == FieldStatus.OK
    assert rec.start_date.status == FieldStatus.OK

    # Los campos blandos no se inventan: degradan a not_found.
    for attr in ("vinculo_type", "role", "employer"):
        f = getattr(rec, attr)
        assert f.status == FieldStatus.NOT_FOUND
        assert f.value is None
        assert f.source is None


# ---------------------------------------------------------------------------
# termination_confirmed: triestado correcto según contexto
# ---------------------------------------------------------------------------

CONTRATO_CON_TERMINACION = (
    "CONTRATO DE TRABAJO. "
    "El contrato regira a partir del 1 de febrero de 2024 hasta el 31 de enero de 2025. "
    "El presente contrato se da por terminado de mutuo acuerdo entre las partes. "
    "Salario mensual: 2.500.000 pesos. Jornada: 48 horas semanales."
)

CONTRATO_SIN_TERMINACION = (
    "CONTRATO DE TRABAJO. El cargo de Asesor comercial sera ejercido. "
    "El contrato regira a partir del 1 de febrero de 2024 hasta el 31 de enero de 2025. "
    "Salario mensual: 2.500.000 pesos. Jornada: 48 horas semanales."
)

CONTRATO_INDEFINIDO = (
    "CONTRATO DE TRABAJO A TERMINO INDEFINIDO. Cargo: Gerente. "
    "Salario mensual: 5.000.000 pesos. Jornada: 42 horas semanales. "
    "El presente contrato no tiene fecha de terminacion pactada."
)


@pytest.mark.asyncio
async def test_termination_confirmed_true_cuando_hay_clausula():
    svc = _service({})
    rec = await svc.extract(CTX, "c-term-true", CONTRATO_CON_TERMINACION)

    assert rec.termination_confirmed.status == FieldStatus.OK
    assert rec.termination_confirmed.value is True
    assert rec.termination_confirmed.source is not None
    assert "terminado" in rec.termination_confirmed.source.text.lower()


@pytest.mark.asyncio
async def test_termination_confirmed_false_cuando_hay_end_date_sin_clausula():
    # Hay end_date pero no hay clausula de terminacion → value=False (zona gris para M3).
    svc = _service({})
    rec = await svc.extract(CTX, "c-term-false", CONTRATO_SIN_TERMINACION)

    assert rec.termination_confirmed.status == FieldStatus.OK
    assert rec.termination_confirmed.value is False
    assert rec.termination_confirmed.source is None  # no hay cita; solo sabemos que falta


@pytest.mark.asyncio
async def test_termination_confirmed_not_found_cuando_no_hay_end_date():
    # Contrato indefinido: sin end_date y sin clausula → not_found.
    svc = _service({})
    rec = await svc.extract(CTX, "c-term-nf", CONTRATO_INDEFINIDO)

    assert rec.termination_confirmed.status == FieldStatus.NOT_FOUND
    assert rec.termination_confirmed.value is None


# ---------------------------------------------------------------------------
# empleado_nombre + empleado_documento (regex determinista)
# ---------------------------------------------------------------------------

CONTRATO_CON_TRABAJADOR = (
    "CONTRATO INDIVIDUAL DE TRABAJO A TERMINO FIJO. "
    "Trabajador: JOSE ANDRES OSPINO, C.C. 1144000000. "
    "Cargo: Vendedor. "
    "Salario mensual: 1.750.905. "
    "Auxilio de transporte: 249.095. "
    "Jornada: 48 horas semanales. "
    "El contrato regira a partir del 1 de enero de 2026 "
    "hasta el 6 de marzo de 2026."
)


@pytest.mark.asyncio
async def test_empleado_nombre_extraido_con_source():
    svc = _service({})
    rec = await svc.extract(CTX, "c-ospino", CONTRATO_CON_TRABAJADOR)

    assert rec.empleado_nombre.status == FieldStatus.OK
    assert "OSPINO" in rec.empleado_nombre.value
    assert rec.empleado_nombre.source is not None
    assert "Trabajador" in rec.empleado_nombre.source.text


@pytest.mark.asyncio
async def test_empleado_documento_extraido_con_source():
    svc = _service({})
    rec = await svc.extract(CTX, "c-ospino-doc", CONTRATO_CON_TRABAJADOR)

    assert rec.empleado_documento.status == FieldStatus.OK
    assert rec.empleado_documento.value == "1144000000"
    assert rec.empleado_documento.source is not None
    assert "C.C" in rec.empleado_documento.source.text


@pytest.mark.asyncio
async def test_empleado_campos_not_found_si_ausentes():
    # El CONTRATO del fixture no tiene "Trabajador: NOMBRE".
    svc = _service({})
    rec = await svc.extract(CTX, "c-sin-trabajador", CONTRATO)

    assert rec.empleado_nombre.status == FieldStatus.NOT_FOUND
    assert rec.empleado_documento.status == FieldStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# auxilio_transporte + salario_variable
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auxilio_transporte_extraido_como_money():
    svc = _service({})
    rec = await svc.extract(CTX, "c-aux", CONTRATO_CON_TRABAJADOR)

    assert rec.auxilio_transporte.status == FieldStatus.OK
    assert rec.auxilio_transporte.value.value == 249095
    assert rec.auxilio_transporte.source is not None
    assert rec.auxilio_transporte.source.doc_id == "c-aux"


@pytest.mark.asyncio
async def test_auxilio_transporte_not_found_si_no_mencionado():
    # El CONTRATO del fixture no menciona auxilio de transporte.
    svc = _service({})
    rec = await svc.extract(CTX, "c-sin-aux", CONTRATO)

    assert rec.auxilio_transporte.status == FieldStatus.NOT_FOUND
    assert rec.auxilio_transporte.value is None


@pytest.mark.asyncio
async def test_salario_variable_false_si_solo_fijo():
    svc = _service({})
    rec = await svc.extract(CTX, "c-fijo", CONTRATO)

    assert rec.salario_variable.status == FieldStatus.OK
    assert rec.salario_variable.value is False
    assert rec.salario_variable.source is None


CONTRATO_CON_COMISIONES = (
    "CONTRATO DE TRABAJO. Cargo de Vendedor. "
    "El salario basico es de 1.750.905 pesos mas comisiones por ventas. "
    "Jornada de 42 horas semanales. "
    "Inicio: 1 de enero de 2026."
)


@pytest.mark.asyncio
async def test_salario_variable_true_con_span_cuando_hay_comisiones():
    svc = _service({})
    rec = await svc.extract(CTX, "c-variable", CONTRATO_CON_COMISIONES)

    assert rec.salario_variable.status == FieldStatus.OK
    assert rec.salario_variable.value is True
    assert rec.salario_variable.source is not None
    assert "comision" in rec.salario_variable.source.text.lower()
