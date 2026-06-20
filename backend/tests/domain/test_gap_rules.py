"""
Tests del motor de compliance (M3). Regla de oro: el codigo decide el gap, no el LLM.
Todos los tests son deterministas: mismo input -> mismo output.
"""
from datetime import date

import pytest

from app.domain.models import DocumentRecord, Field
from app.domain.compliance.gap_rules import detect_gaps

# Fecha de referencia fija para todos los tests (no depende de date.today())
REF = date(2026, 6, 18)


def _record(
    *,
    vinculo: str = "termino_indefinido",
    hours: float = 42,
    start: str = "2026-06-01",
    end: str | None = None,
    pago_ss_mora: bool | None = None,
) -> DocumentRecord:
    """Factory minima de DocumentRecord para tests de gap_rules."""
    mora_field = Field(value=pago_ss_mora) if pago_ss_mora is not None else None
    return DocumentRecord(
        doc_id="test-001",
        vinculo_type=Field(value=vinculo),
        base_salary=Field(value={"value": 2_500_000, "currency": "COP", "periodicity": "mensual"}),
        start_date=Field(value=start),
        end_date=Field(value=end),
        weekly_hours=Field(value=hours),
        role=Field(value="Asesor comercial"),
        employer=Field(value={"name": "Empresa SAS"}),
        empleado_nombre=Field(value="Trabajador Test"),
        empleado_documento=Field(value="79.000.000"),
        auxilio_transporte=Field(value=None, status="not_found"),
        salario_variable=Field(value=False),
        pago_ss_mora=mora_field,
    )


# ── Test 1: Jornada 48h → gap "alta" con norma Ley 2101 ─────────────────────

def test_jornada_48h_genera_gap_alta():
    rec = _record(hours=48)
    gaps = detect_gaps(rec, reference_date=REF)
    jornada = [g for g in gaps if g.gap_id == "g1"]
    assert len(jornada) == 1, "Debe haber exactamente un gap de jornada"
    g = jornada[0]
    assert g.severity == "alta"
    assert g.norm_id == "Ley 2101/2021"
    assert g.article == "art. 3"
    assert g.remedy_type == "otrosi"


def test_jornada_42h_no_genera_gap():
    """Exactamente en el limite -> no dispara gap."""
    rec = _record(hours=42)
    gaps = detect_gaps(rec, reference_date=REF)
    assert all(g.gap_id != "g1" for g in gaps)


# ── Test 2: prestacion_servicios → gap de reclasificacion con Ley 2466 ───────

def test_prestacion_servicios_genera_gap_reclasificacion():
    rec = _record(vinculo="prestacion_servicios")
    gaps = detect_gaps(rec, reference_date=REF)
    reclas = [g for g in gaps if g.gap_id == "g2"]
    assert len(reclas) == 1
    g = reclas[0]
    assert g.norm_id == "Ley 2466/2025"
    assert g.article == "art. 5"
    assert g.remedy_type == "contrato_corregido"


# ── Test 3: Contrato conforme → cero gaps ────────────────────────────────────

def test_contrato_conforme_cero_gaps():
    """
    42h, indefinido, inicio reciente, sin pago_ss_mora -> cero gaps.
    """
    rec = _record(hours=42, vinculo="termino_indefinido", start="2026-06-01")
    gaps = detect_gaps(rec, reference_date=REF)
    # REF=2026-06-18: 17 dias → no g3; no pago_ss_mora → no g5
    assert gaps == [], f"Se esperaban 0 gaps, se obtuvieron: {gaps}"


# ── Test 4: Determinismo ─────────────────────────────────────────────────────

def test_determinismo_mismo_record_mismos_gaps():
    """Mismo record + reference_date -> resultado identico en dos llamadas."""
    rec = _record(hours=48, vinculo="prestacion_servicios", start="2024-01-01")
    result_a = detect_gaps(rec, reference_date=REF)
    result_b = detect_gaps(rec, reference_date=REF)
    assert result_a == result_b


# ── Tests adicionales de las reglas nuevas ───────────────────────────────────

def test_vacaciones_mas_de_un_anio():
    """Contrato laborado mas de 365 dias -> gap g3 vacaciones."""
    rec = _record(vinculo="termino_indefinido", hours=42, start="2024-12-01")
    gaps = detect_gaps(rec, reference_date=REF)
    vac_gaps = [g for g in gaps if g.gap_id == "g3"]
    assert len(vac_gaps) == 1
    assert vac_gaps[0].norm_id == "CST"
    assert vac_gaps[0].article == "art. 186"


def test_vencimiento_termino_fijo_menos_30_dias():
    """Termino fijo que vence en < 30 dias -> gap g4 severidad 'alta'."""
    rec = _record(vinculo="termino_fijo", hours=42, start="2025-07-01", end="2026-07-01")
    gaps = detect_gaps(rec, reference_date=REF)
    venc = [g for g in gaps if g.gap_id == "g4"]
    assert len(venc) == 1
    assert venc[0].severity == "alta"
    assert venc[0].norm_id == "CST"
    assert venc[0].article == "art. 46"


def test_vencimiento_termino_fijo_entre_30_y_90_dias():
    """Termino fijo que vence entre 30 y 90 dias -> severidad 'media'."""
    rec = _record(vinculo="termino_fijo", hours=42, start="2025-07-01", end="2026-08-15")
    gaps = detect_gaps(rec, reference_date=REF)
    venc = [g for g in gaps if g.gap_id == "g4"]
    assert len(venc) == 1
    assert venc[0].severity == "media"


def test_seguridad_social_con_mora_comprobada_genera_gap():
    """pago_ss_mora=True en vinculo laboral -> gap g5 alta (mora comprobada)."""
    rec = _record(vinculo="termino_indefinido", hours=42, start="2026-05-01", pago_ss_mora=True)
    gaps = detect_gaps(rec, reference_date=REF)
    ss_gaps = [g for g in gaps if g.gap_id == "g5"]
    assert len(ss_gaps) == 1
    assert ss_gaps[0].norm_id == "Ley 100/1993"
    assert ss_gaps[0].severity == "alta"


def test_seguridad_social_sin_mora_no_genera_gap():
    """Sin pago_ss_mora -> no hay g5, aunque el contrato lleve meses activo."""
    rec = _record(vinculo="termino_indefinido", hours=42, start="2024-01-01")
    gaps = detect_gaps(rec, reference_date=REF)
    assert all(g.gap_id != "g5" for g in gaps)


def test_prestacion_servicios_no_genera_gap_seguridad_social():
    """prestacion_servicios NO es vinculo laboral -> no genera g5."""
    rec = _record(vinculo="prestacion_servicios", start="2024-01-01")
    gaps = detect_gaps(rec, reference_date=REF)
    assert all(g.gap_id != "g5" for g in gaps)


# ── Edge cases: robustez ante datos incompletos o malformados ─────────────────

def test_weekly_hours_none_no_genera_gap_jornada():
    """Si weekly_hours.value es None (campo no extraido), no se afirma g1."""
    rec = DocumentRecord(
        doc_id="test-null",
        vinculo_type=Field(value="termino_indefinido"),
        base_salary=Field(value=None),
        start_date=Field(value="2026-06-01"),
        end_date=Field(value=None),
        weekly_hours=Field(value=None, status="not_found"),
        role=Field(value=None),
        employer=Field(value=None),
        empleado_nombre=Field(value=None, status="not_found"),
        empleado_documento=Field(value=None, status="not_found"),
        auxilio_transporte=Field(value=None, status="not_found"),
        salario_variable=Field(value=False),
    )
    gaps = detect_gaps(rec, reference_date=REF)
    assert all(g.gap_id != "g1" for g in gaps)


def test_weekly_hours_string_no_genera_gap_jornada():
    """Si el extractor devolvio texto en vez de numero, no explota ni afirma g1."""
    rec = _record(hours=42)
    # Sobreescribimos el valor con un string (error de extraccion)
    from app.domain.models import Field as F
    rec2 = rec.model_copy(update={"weekly_hours": F(value="cuarenta y ocho")})
    gaps = detect_gaps(rec2, reference_date=REF)
    assert all(g.gap_id != "g1" for g in gaps)


def test_fecha_malformada_no_explota():
    """Fecha no parseable → detect_gaps no lanza excepcion y no afirma gaps de fecha."""
    rec = _record(vinculo="termino_indefinido", hours=42, start="fecha-invalida")
    gaps = detect_gaps(rec, reference_date=REF)
    # No debe haber g3 ni g5 (no se pueden calcular sin fecha valida)
    assert all(g.gap_id not in ("g3", "g5") for g in gaps)


def test_termino_fijo_sin_end_date_no_genera_vencimiento():
    """Termino fijo sin end_date (campo not_found) no genera alerta de vencimiento."""
    rec = _record(vinculo="termino_fijo", hours=42, start="2025-01-01", end=None)
    gaps = detect_gaps(rec, reference_date=REF)
    assert all(g.gap_id != "g4" for g in gaps)


def test_termino_fijo_vence_en_91_dias_no_alerta():
    """Vence en 91 dias: fuera del umbral de 90 -> no genera g4."""
    # REF = 2026-06-18, + 91 dias = 2026-09-17
    rec = _record(vinculo="termino_fijo", hours=42, start="2025-01-01", end="2026-09-17")
    gaps = detect_gaps(rec, reference_date=REF)
    assert all(g.gap_id != "g4" for g in gaps)


def test_jornada_limite_exacto_no_genera_gap():
    """Exactamente 42h -> no supera el limite, no hay gap."""
    rec = _record(hours=42.0)
    gaps = detect_gaps(rec, reference_date=REF)
    assert all(g.gap_id != "g1" for g in gaps)


def test_jornada_42_1h_genera_gap():
    """42.1h ya supera el limite de 42h -> g1."""
    rec = _record(hours=42.1)
    gaps = detect_gaps(rec, reference_date=REF)
    assert any(g.gap_id == "g1" for g in gaps)


def test_duracion_exacta_365_dias_no_genera_vacaciones():
    """365 dias exactos NO supera el umbral (> 365), no hay g3."""
    # REF = 2026-06-18, start exactamente 365 dias antes = 2025-06-18
    rec = _record(vinculo="termino_indefinido", hours=42, start="2025-06-18")
    gaps = detect_gaps(rec, reference_date=REF)
    # (2026-06-18 - 2025-06-18).days = 365, que NO es > 365
    assert all(g.gap_id != "g3" for g in gaps)


def test_duracion_366_dias_genera_vacaciones():
    """366 dias (> 365) si genera g3."""
    rec = _record(vinculo="termino_indefinido", hours=42, start="2025-06-17")
    gaps = detect_gaps(rec, reference_date=REF)
    assert any(g.gap_id == "g3" for g in gaps)


def test_obra_labor_con_mora_genera_gap_seguridad_social():
    """obra_labor con pago_ss_mora=True -> g5 alta."""
    rec = _record(vinculo="obra_labor", hours=42, start="2026-05-01", pago_ss_mora=True)
    gaps = detect_gaps(rec, reference_date=REF)
    assert any(g.gap_id == "g5" for g in gaps)


def test_pago_ss_mora_false_no_genera_gap():
    """pago_ss_mora=False (pagos al dia verificados) -> no g5."""
    rec = DocumentRecord(
        doc_id="test-pagofalse",
        vinculo_type=Field(value="termino_indefinido"),
        base_salary=Field(value=None),
        start_date=Field(value="2024-01-01"),
        end_date=Field(value=None),
        weekly_hours=Field(value=42),
        role=Field(value=None),
        employer=Field(value=None),
        empleado_nombre=Field(value=None, status="not_found"),
        empleado_documento=Field(value=None, status="not_found"),
        auxilio_transporte=Field(value=None, status="not_found"),
        salario_variable=Field(value=False),
        pago_ss_mora=Field(value=False),
    )
    gaps = detect_gaps(rec, reference_date=REF)
    assert all(g.gap_id != "g5" for g in gaps)
