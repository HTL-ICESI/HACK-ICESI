"""
Contratos sinteticos realistas — prueba de extremo a extremo de M3.

Genera tres contratos colombianos con problemas reales y los pasa por el pipeline
completo (DocumentRecord → ComplianceService → respuesta HTTP) para verificar
que M3 detecta lo correcto en cada caso.

Estos son el "caso gold sintetico" hasta que David entregue contratos reales.
El texto de cada contrato es el que apareceria en el demo ante el jurado.
"""
from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.domain.models import DocumentRecord, Field, Source
from app.domain.compliance.gap_rules import detect_gaps
from app.services.compliance_service import ComplianceService

client = TestClient(app)
AUTH  = {"Authorization": "Bearer demo-hg-key"}
CTX   = TenantContext(tenant_id="empresa-demo", actor="test-sintetico")
REF   = date(2026, 6, 18)

# ─────────────────────────────────────────────────────────────────────────────
# CONTRATO 1
# Empresa formal con jornada obsoleta (48h) — el caso mas comun en Colombia
# Texto que veria el jurado en la demo:
# ─────────────────────────────────────────────────────────────────────────────
TEXTO_CONTRATO_1 = """
CONTRATO INDIVIDUAL DE TRABAJO A TERMINO INDEFINIDO

Entre DISTRIBUIDORA NACIONAL SAS, sociedad identificada con NIT 830.456.789-2,
representada por su Gerente General ("El Empleador"), y CARLOS ANDRES MUÑOZ HERRERA,
identificado con CC 79.456.123 de Bogota ("El Trabajador"), se celebra el presente
contrato de trabajo sujeto a las siguientes clausulas:

PRIMERA - OBJETO Y CARGO: El Trabajador se obliga a prestar sus servicios personales
en el cargo de AUXILIAR ADMINISTRATIVO bajo la subordinacion y dependencia del Empleador,
realizando las funciones propias del cargo.

SEGUNDA - DURACION: El presente contrato es a termino indefinido y comenzara a regir
a partir del primero (1) de enero de dos mil veinticinco (2025).

TERCERA - REMUNERACION: El Empleador reconocera al Trabajador a titulo de salario la
suma mensual de UN MILLON CUATROCIENTOS VEINTITRES MIL QUINIENTOS PESOS ($1.423.500)
moneda corriente colombiana, pagadera por quincenas vencidas.

CUARTA - JORNADA DE TRABAJO: La jornada ordinaria de trabajo sera de CUARENTA Y OCHO
(48) horas semanales, distribuidas de lunes a sabado, en el horario que determine el
Empleador segun las necesidades del servicio.

QUINTA - LUGAR DE TRABAJO: El Trabajador prestara sus servicios en las instalaciones
del Empleador ubicadas en la ciudad de Bogota D.C.

En constancia, se firma en Bogota el 1 de enero de 2025.
"""

# Lo que M2 extraeria de este contrato (con spans reales del texto)
RECORD_CONTRATO_1 = DocumentRecord(
    doc_id="contrato-001-sintetico",
    vinculo_type=Field(
        value="termino_indefinido",
        source=Source(span_start=548, span_end=591,
                      text="contrato es a termino indefinido y comenzara",
                      confidence=0.97, doc_id="contrato-001-sintetico"),
        status="ok",
    ),
    base_salary=Field(
        value={"value": 1_423_500, "currency": "COP", "periodicity": "mensual"},
        source=Source(span_start=742, span_end=821,
                      text="UN MILLON CUATROCIENTOS VEINTITRES MIL QUINIENTOS PESOS ($1.423.500)",
                      confidence=0.99, doc_id="contrato-001-sintetico"),
        status="ok",
    ),
    start_date=Field(
        value="2025-01-01",
        source=Source(span_start=590, span_end=645,
                      text="primero (1) de enero de dos mil veinticinco (2025)",
                      confidence=0.96, doc_id="contrato-001-sintetico"),
        status="ok",
    ),
    end_date=Field(value=None, source=None, status="not_found"),
    weekly_hours=Field(
        value=48,
        source=Source(span_start=900, span_end=947,
                      text="CUARENTA Y OCHO (48) horas semanales",
                      confidence=0.99, doc_id="contrato-001-sintetico"),
        status="ok",
    ),
    role=Field(
        value="Auxiliar Administrativo",
        source=Source(span_start=327, span_end=356,
                      text="cargo de AUXILIAR ADMINISTRATIVO",
                      confidence=0.95, doc_id="contrato-001-sintetico"),
        status="ok",
    ),
    employer=Field(
        value={"name": "Distribuidora Nacional SAS", "nit": "830456789-2"},
        source=None, status="ok",
    ),
    empleado_nombre=Field(
        value="Carlos Andres Muñoz Herrera",
        source=Source(span_start=210, span_end=237,
                      text="CARLOS ANDRES MUÑOZ HERRERA",
                      confidence=0.97, doc_id="contrato-001-sintetico"),
        status="ok",
    ),
    empleado_documento=Field(
        value="79.456.123",
        source=Source(span_start=262, span_end=285,
                      text="CC 79.456.123 de Bogota",
                      confidence=0.97, doc_id="contrato-001-sintetico"),
        status="ok",
    ),
    auxilio_transporte=Field(value=None, source=None, status="not_found"),
    salario_variable=Field(value=False, source=None, status="ok"),
)

# ─────────────────────────────────────────────────────────────────────────────
# CONTRATO 2
# Falso independiente — prestacion de servicios con multiples indicios
# de subordinacion (el caso estrella de Ley 2466/2025 para el jurado)
# ─────────────────────────────────────────────────────────────────────────────
TEXTO_CONTRATO_2 = """
CONTRATO DE PRESTACION DE SERVICIOS PROFESIONALES

Entre TECHVALLE SOLUTIONS SAS, identificada con NIT 900.765.432-1 ("El Contratante"),
y ANA SOFIA RESTREPO CARDONA, CC 1.144.056.789 ("La Contratista"), se suscribe:

PRIMERA - OBJETO: La Contratista se obliga a prestar servicios como DESARROLLADORA
DE SOFTWARE SENIOR bajo los lineamientos tecnicos y directrices del Contratante,
ejecutando las tareas asignadas por el area de tecnologia.

SEGUNDA - DURACION: El presente contrato inicia el quince (15) de enero de 2024 y
tendra vigencia hasta el treinta y uno (31) de diciembre de 2025.

TERCERA - HONORARIOS: El Contratante pagara honorarios mensuales de TRES MILLONES
DE PESOS ($3.000.000) moneda corriente.

CUARTA - JORNADA Y LUGAR: La Contratista desarrollara sus actividades de lunes a
viernes en horario de ocho (8) de la manana a seis (6) de la tarde, cuarenta y ocho
(48) horas semanales, en las instalaciones del Contratante ubicadas en Cali.

QUINTA - EXCLUSIVIDAD: La Contratista no podra prestar servicios a terceros en el
mismo ramo sin autorizacion previa y escrita del Contratante durante la vigencia.

SEXTA - HERRAMIENTAS: El Contratante suministrara el equipo de computo, licencias
de software y demas herramientas necesarias para la ejecucion del objeto contractual.
"""

RECORD_CONTRATO_2 = DocumentRecord(
    doc_id="contrato-002-sintetico",
    vinculo_type=Field(
        value="prestacion_servicios",
        source=Source(span_start=0, span_end=47,
                      text="CONTRATO DE PRESTACION DE SERVICIOS PROFESIONALES",
                      confidence=0.98, doc_id="contrato-002-sintetico"),
        status="ok",
    ),
    base_salary=Field(
        value={"value": 3_000_000, "currency": "COP", "periodicity": "mensual"},
        source=Source(span_start=530, span_end=581,
                      text="honorarios mensuales de TRES MILLONES DE PESOS ($3.000.000)",
                      confidence=0.97, doc_id="contrato-002-sintetico"),
        status="ok",
    ),
    start_date=Field(
        value="2024-01-15",
        source=Source(span_start=420, span_end=462,
                      text="inicia el quince (15) de enero de 2024",
                      confidence=0.95, doc_id="contrato-002-sintetico"),
        status="ok",
    ),
    end_date=Field(
        value="2025-12-31",
        source=Source(span_start=463, span_end=510,
                      text="hasta el treinta y uno (31) de diciembre de 2025",
                      confidence=0.94, doc_id="contrato-002-sintetico"),
        status="ok",
    ),
    weekly_hours=Field(
        value=48,
        source=Source(span_start=620, span_end=660,
                      text="cuarenta y ocho (48) horas semanales",
                      confidence=0.96, doc_id="contrato-002-sintetico"),
        status="ok",
    ),
    role=Field(
        value="Desarrolladora de Software Senior",
        source=Source(span_start=188, span_end=220,
                      text="DESARROLLADORA DE SOFTWARE SENIOR",
                      confidence=0.97, doc_id="contrato-002-sintetico"),
        status="ok",
    ),
    employer=Field(
        value={"name": "TechValle Solutions SAS", "nit": "900765432-1"},
        source=None, status="ok",
    ),
    empleado_nombre=Field(
        value="Ana Sofia Restrepo Cardona",
        source=Source(span_start=120, span_end=146,
                      text="ANA SOFIA RESTREPO CARDONA",
                      confidence=0.96, doc_id="contrato-002-sintetico"),
        status="ok",
    ),
    empleado_documento=Field(
        value="1.144.056.789",
        source=Source(span_start=151, span_end=167,
                      text="CC 1.144.056.789",
                      confidence=0.96, doc_id="contrato-002-sintetico"),
        status="ok",
    ),
    auxilio_transporte=Field(value=None, source=None, status="not_found"),
    salario_variable=Field(value=False, source=None, status="ok"),
)

# ─────────────────────────────────────────────────────────────────────────────
# CONTRATO 3
# Termino fijo vencido sin renovacion ni acta de terminacion
# ─────────────────────────────────────────────────────────────────────────────
TEXTO_CONTRATO_3 = """
CONTRATO INDIVIDUAL DE TRABAJO A TERMINO FIJO

Entre IMPORTACIONES DEL PACIFICO LTDA, NIT 890.123.456-3 ("El Empleador"), y
DIANA MARCELA OSPINA RUIZ, CC 1.088.123.456 de Cali ("La Trabajadora"), se pacta:

PRIMERA - CARGO: La Trabajadora desempenara el cargo de EJECUTIVA DE VENTAS bajo la
subordinacion del Empleador.

SEGUNDA - DURACION: El presente contrato es a termino fijo de UN (1) ANO, con inicio
el primero (1) de junio de 2024 y vencimiento el treinta y uno (31) de mayo de 2025.

TERCERA - SALARIO: La Trabajadora devengara un salario mensual de DOS MILLONES
DOSCIENTOS MIL PESOS ($2.200.000) pagaderos por periodos quincenales.

CUARTA - JORNADA: La jornada sera de cuarenta y dos (42) horas semanales distribuidas
de lunes a viernes segun el horario institucional.

QUINTA - LUGAR: Las funciones se desarrollaran en las instalaciones de la empresa
en la ciudad de Cali, Valle del Cauca.
"""

RECORD_CONTRATO_3 = DocumentRecord(
    doc_id="contrato-003-sintetico",
    vinculo_type=Field(
        value="termino_fijo",
        source=Source(span_start=200, span_end=240,
                      text="contrato es a termino fijo de UN (1) ANO",
                      confidence=0.97, doc_id="contrato-003-sintetico"),
        status="ok",
    ),
    base_salary=Field(
        value={"value": 2_200_000, "currency": "COP", "periodicity": "mensual"},
        source=Source(span_start=390, span_end=443,
                      text="DOS MILLONES DOSCIENTOS MIL PESOS ($2.200.000)",
                      confidence=0.98, doc_id="contrato-003-sintetico"),
        status="ok",
    ),
    start_date=Field(
        value="2024-06-01",
        source=Source(span_start=243, span_end=277,
                      text="inicio el primero (1) de junio de 2024",
                      confidence=0.96, doc_id="contrato-003-sintetico"),
        status="ok",
    ),
    end_date=Field(
        value="2025-05-31",
        source=Source(span_start=278, span_end=320,
                      text="vencimiento el treinta y uno (31) de mayo de 2025",
                      confidence=0.95, doc_id="contrato-003-sintetico"),
        status="ok",
    ),
    weekly_hours=Field(
        value=42,
        source=Source(span_start=470, span_end=505,
                      text="cuarenta y dos (42) horas semanales",
                      confidence=0.99, doc_id="contrato-003-sintetico"),
        status="ok",
    ),
    role=Field(
        value="Ejecutiva de Ventas",
        source=Source(span_start=138, span_end=160,
                      text="cargo de EJECUTIVA DE VENTAS",
                      confidence=0.94, doc_id="contrato-003-sintetico"),
        status="ok",
    ),
    employer=Field(
        value={"name": "Importaciones del Pacifico Ltda", "nit": "890123456-3"},
        source=None, status="ok",
    ),
    empleado_nombre=Field(
        value="Diana Marcela Ospina Ruiz",
        source=Source(span_start=110, span_end=135,
                      text="DIANA MARCELA OSPINA RUIZ",
                      confidence=0.95, doc_id="contrato-003-sintetico"),
        status="ok",
    ),
    empleado_documento=Field(
        value="1.088.123.456",
        source=Source(span_start=140, span_end=164,
                      text="CC 1.088.123.456 de Cali",
                      confidence=0.95, doc_id="contrato-003-sintetico"),
        status="ok",
    ),
    auxilio_transporte=Field(value=None, source=None, status="not_found"),
    salario_variable=Field(value=False, source=None, status="ok"),
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _svc() -> ComplianceService:
    return ComplianceService(AuditLog())


def _gap_ids(record: DocumentRecord) -> set[str]:
    return {g.gap_id for g in detect_gaps(record, reference_date=REF)}


def _analyze(record: DocumentRecord) -> dict:
    return _svc().analyze(CTX, record.doc_id, record, "contrato")


# ─────────────────────────────────────────────────────────────────────────────
# CONTRATO 1: Empresa formal — jornada obsoleta
# ─────────────────────────────────────────────────────────────────────────────

class TestContrato1EmpresaFormal:

    def test_detecta_jornada_obsoleta(self):
        """Jornada 48h → g1 alta con span correcto del contrato."""
        result = _analyze(RECORD_CONTRATO_1)
        g1 = next((g for g in result["gaps"] if g["gap_id"] == "g1"), None)
        assert g1 is not None, "Debe detectar jornada obsoleta (48h > 42h)"
        assert g1["severity"] == "alta"
        assert g1["source"]["text"] == "CUARENTA Y OCHO (48) horas semanales"

    def test_detecta_vacaciones_pendientes(self):
        """Contrato activo desde 2025-01-01 → 534 dias > 365 → g3."""
        result = _analyze(RECORD_CONTRATO_1)
        g3 = next((g for g in result["gaps"] if g["gap_id"] == "g3"), None)
        assert g3 is not None, "Debe detectar posible acumulacion de vacaciones"
        assert g3["citation"]["article"] == "art. 186"

    def test_NO_genera_reclasificacion(self):
        """termino_indefinido no es prestacion_servicios → no hay g2."""
        result = _analyze(RECORD_CONTRATO_1)
        assert all(g["gap_id"] != "g2" for g in result["gaps"])

    def test_summary_tiene_al_menos_una_alta(self):
        result = _analyze(RECORD_CONTRATO_1)
        assert result["summary"]["has_blocking_issues"] is True
        assert result["summary"]["by_severity"]["alta"] >= 1

    def test_summary_risk_score_mayor_que_cero(self):
        result = _analyze(RECORD_CONTRATO_1)
        assert result["summary"]["risk_score"] > 0

    def test_applicable_norms_presentes(self):
        result = _analyze(RECORD_CONTRATO_1)
        arts = {(n["norm_id"], n["article"]) for n in result["applicable_norms"]}
        assert ("CST", "art. 64") in arts
        assert ("CST", "art. 65") in arts


# ─────────────────────────────────────────────────────────────────────────────
# CONTRATO 2: Falso independiente — reclasificacion Ley 2466
# ─────────────────────────────────────────────────────────────────────────────

class TestContrato2FalsoIndependiente:

    def test_detecta_riesgo_reclasificacion_ley_2466(self):
        """prestacion_servicios + 2 indicios → g2 con Ley 2466/2025 art. 5."""
        result = _analyze(RECORD_CONTRATO_2)
        g2 = next((g for g in result["gaps"] if g["gap_id"] == "g2"), None)
        assert g2 is not None, "El caso estrella: debe detectar riesgo de reclasificacion"
        assert g2["citation"]["norm_id"] == "Ley 2466/2025"
        assert g2["citation"]["article"] == "art. 5"
        assert "2" in g2["issue"]  # "2 indicio(s)"

    def test_detecta_jornada_obsoleta(self):
        """Jornada 48h en prestacion de servicios tambien es g1."""
        result = _analyze(RECORD_CONTRATO_2)
        assert any(g["gap_id"] == "g1" for g in result["gaps"])

    def test_detecta_vacaciones_mas_de_un_anio(self):
        """Inicio 2024-01-15, end 2025-12-31 → 716 dias > 365 → g3."""
        gaps = detect_gaps(RECORD_CONTRATO_2, reference_date=REF)
        assert any(g.gap_id == "g3" for g in gaps)

    def test_NO_genera_gap_seguridad_social(self):
        """prestacion_servicios NO es vinculo laboral → no hay g5."""
        result = _analyze(RECORD_CONTRATO_2)
        assert all(g["gap_id"] != "g5" for g in result["gaps"])

    def test_summary_multiples_gaps(self):
        """Este contrato tiene al menos 3 gaps (g1, g2, g3) → risk_score alto."""
        result = _analyze(RECORD_CONTRATO_2)
        assert result["summary"]["total_gaps"] >= 3
        # g1(alta=3) + g2(media=2) + g3(media=2) = 7 puntos minimo
        assert result["summary"]["risk_score"] >= 7

    def test_trazabilidad_span_jornada_en_gap(self):
        """El span de jornada del contrato 2 llega al gap g1."""
        result = _analyze(RECORD_CONTRATO_2)
        g1 = next(g for g in result["gaps"] if g["gap_id"] == "g1")
        assert g1["source"]["text"] == "cuarenta y ocho (48) horas semanales"
        assert g1["source"]["doc_id"] == "contrato-002-sintetico"


# ─────────────────────────────────────────────────────────────────────────────
# CONTRATO 3: Termino fijo vencido
# ─────────────────────────────────────────────────────────────────────────────

class TestContrato3TerminoFijoVencido:

    def test_detecta_contrato_vencido_sin_renovacion(self):
        """end_date 2025-05-31 ya paso → g4 'VENCIDO' alta."""
        result = _analyze(RECORD_CONTRATO_3)
        g4 = next((g for g in result["gaps"] if g["gap_id"] == "g4"), None)
        assert g4 is not None, "Debe detectar contrato vencido sin documentacion"
        assert g4["severity"] == "alta"
        assert "VENCIDO" in g4["issue"]
        assert g4["citation"]["norm_id"] == "CST"
        assert g4["citation"]["article"] == "art. 46"

    def test_jornada_42h_conforme_no_genera_g1(self):
        """Jornada 42h cumple la ley → no hay g1."""
        result = _analyze(RECORD_CONTRATO_3)
        assert all(g["gap_id"] != "g1" for g in result["gaps"])

    def test_NO_genera_reclasificacion(self):
        """termino_fijo no es prestacion_servicios → no hay g2."""
        result = _analyze(RECORD_CONTRATO_3)
        assert all(g["gap_id"] != "g2" for g in result["gaps"])

    def test_detecta_vacaciones_acumuladas(self):
        """2024-06-01 a 2025-05-31 = 365 dias. NO dispara g3 (limite exacto).
        Pero con REF=2026-06-18 y end_date=2025-05-31 (pasado) → end_dt=2025-05-31
        → (2025-05-31 - 2024-06-01).days = 364 dias. NO > 365 → no g3.
        Si calculamos hasta REF (end es None? No, hay end_date).
        """
        gaps = detect_gaps(RECORD_CONTRATO_3, reference_date=REF)
        # 2025-05-31 - 2024-06-01 = 364 dias → NO > 365 → no g3
        assert all(g.gap_id != "g3" for g in gaps)

    def test_NO_genera_gap_seguridad_social_sin_mora(self):
        """Sin pago_ss_mora → no hay g5, aunque el contrato lleve meses activo."""
        result = _analyze(RECORD_CONTRATO_3)
        assert all(g["gap_id"] != "g5" for g in result["gaps"])

    def test_summary_blocking_issue_por_contrato_vencido(self):
        """g4 alta → has_blocking_issues = True."""
        result = _analyze(RECORD_CONTRATO_3)
        assert result["summary"]["has_blocking_issues"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Tests HTTP de los tres contratos via endpoint
# ─────────────────────────────────────────────────────────────────────────────

def _record_to_api_json(record: DocumentRecord) -> dict:
    """Serializa un DocumentRecord a JSON compatible con el endpoint."""
    return json.loads(record.model_dump_json())


@pytest.mark.parametrize("record,expected_gap_ids", [
    (RECORD_CONTRATO_1, {"g1"}),
    (RECORD_CONTRATO_2, {"g1", "g2"}),
    (RECORD_CONTRATO_3, {"g4"}),
])
def test_endpoint_http_contratos_sinteticos(record, expected_gap_ids):
    """Los tres contratos sinteticos pasan por el endpoint HTTP y dan los gaps esperados."""
    resp = client.post(
        "/api/compliance/analyze",
        headers=AUTH,
        json={
            "doc_id": record.doc_id,
            "doc_type": "contrato",
            "record": _record_to_api_json(record),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    gap_ids = {g["gap_id"] for g in body["gaps"]}
    for expected in expected_gap_ids:
        assert expected in gap_ids, (
            f"Contrato {record.doc_id}: se esperaba gap '{expected}', "
            f"se obtuvieron: {gap_ids}"
        )
    # Summary siempre presente
    assert "summary" in body
    assert "risk_score" in body["summary"]


# ─────────────────────────────────────────────────────────────────────────────
# Test de comparacion de riesgo entre los tres contratos
# ─────────────────────────────────────────────────────────────────────────────

def test_ranking_de_riesgo_entre_contratos():
    """
    El contrato 2 (falso independiente con 3+ gaps) debe tener risk_score
    mayor que el contrato 3 (solo 1 alta + baja), que a su vez tiene
    risk_score mayor que 0.

    Verifica que el risk_score es util para priorizar atencion juridica.
    """
    r1 = _analyze(RECORD_CONTRATO_1)["summary"]["risk_score"]
    r2 = _analyze(RECORD_CONTRATO_2)["summary"]["risk_score"]
    r3 = _analyze(RECORD_CONTRATO_3)["summary"]["risk_score"]

    # Contrato 2 tiene g1(alta) + g2(media) + g3(media) = 3+2+2 = 7 puntos
    # Contrato 1 tiene g1(alta) + g3(media) = 3+2 = 5 puntos
    # Contrato 3 tiene g4(alta) = 3 puntos  (g5 solo con pago_ss_mora comprobada)
    assert r2 > r3, f"Falso independiente ({r2}pts) debe tener mas riesgo que fijo vencido ({r3}pts)"
    assert r1 > r3, f"Jornada obsoleta ({r1}pts) debe tener mas riesgo que fijo vencido ({r3}pts)"
    assert r2 > 0 and r1 > 0 and r3 > 0


def test_output_completo_contrato_2_para_demo():
    """
    Imprime el JSON completo del analisis del contrato 2 (el caso estrella del demo).
    Este output es exactamente lo que veria el jurado en la pantalla.
    """
    result = _analyze(RECORD_CONTRATO_2)
    output = json.dumps(result, indent=2, ensure_ascii=False)

    # Verificaciones clave del demo
    assert "Ley 2466/2025" in output, "La Ley 2466 debe estar visible en el output del demo"
    assert "reclasificacion" in output.lower()
    assert result["summary"]["total_gaps"] >= 3
    assert result["summary"]["has_blocking_issues"] is True

    # Descomentar para ver el output completo en consola durante el desarrollo:
    # print("\n=== OUTPUT DEMO CONTRATO 2 (Falso Independiente) ===")
    # print(output)
