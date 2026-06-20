"""
Test de integracion M2 → M3.

Usa el response_example EXACTO de contracts.json como input de M3,
simulando el flujo real: M2 extrae → M3 analiza.

Esto verifica que el contrato JSON entre modulos es compatible
y que M3 detecta los gaps esperados en el ejemplo de HG.
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.domain.models import DocumentRecord, Field, Source, Money
from app.domain.compliance.gap_rules import detect_gaps
from app.services.compliance_service import ComplianceService

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}
CTX = TenantContext(tenant_id="empresa-hg", actor="test-pipeline")

# ── Ejemplo real de contracts.json (response_example de M2) ──────────────────
# Contrato: termino_fijo, 48h, 2024-02-01 a 2025-01-31, salario 2.5M

M2_EXAMPLE_RECORD = DocumentRecord(
    doc_id="contrato-001",
    vinculo_type=Field(
        value="termino_fijo",
        source=Source(span_start=340, span_end=372,
                      text="contrato a termino fijo de un (1) ano",
                      confidence=0.95, doc_id="contrato-001"),
        status="ok",
    ),
    base_salary=Field(
        value={"value": 2_500_000, "currency": "COP", "periodicity": "mensual"},
        source=Source(span_start=1820, span_end=1875,
                      text="salario mensual de DOS MILLONES QUINIENTOS MIL PESOS",
                      confidence=0.98, doc_id="contrato-001"),
        status="ok",
    ),
    start_date=Field(
        value="2024-02-01",
        source=Source(span_start=410, span_end=440,
                      text="a partir del 1 de febrero de 2024",
                      confidence=0.96, doc_id="contrato-001"),
        status="ok",
    ),
    end_date=Field(
        value="2025-01-31",
        source=Source(span_start=442, span_end=470,
                      text="hasta el 31 de enero de 2025",
                      confidence=0.94, doc_id="contrato-001"),
        status="ok",
    ),
    weekly_hours=Field(
        value=48,
        source=Source(span_start=980, span_end=1010,
                      text="jornada de cuarenta y ocho horas",
                      confidence=0.9, doc_id="contrato-001"),
        status="ok",
    ),
    role=Field(
        value="Asesor comercial",
        source=Source(span_start=250, span_end=280,
                      text="cargo de Asesor comercial",
                      confidence=0.92, doc_id="contrato-001"),
        status="ok",
    ),
    employer=Field(
        value={"name": "Empresa Cliente SAS", "nit": "900123456-7"},
        source=None,
        status="ok",
    ),
    empleado_nombre=Field(
        value="Trabajador HG",
        source=Source(span_start=150, span_end=170,
                      text="el Trabajador HG",
                      confidence=0.9, doc_id="contrato-001"),
        status="ok",
    ),
    empleado_documento=Field(
        value="79.123.456",
        source=Source(span_start=175, span_end=195,
                      text="CC 79.123.456",
                      confidence=0.9, doc_id="contrato-001"),
        status="ok",
    ),
    auxilio_transporte=Field(value=None, source=None, status="not_found"),
    salario_variable=Field(value=False, source=None, status="ok"),
)

# Fecha de referencia fija para que los resultados sean reproducibles
REF = date(2026, 6, 18)


# ── Tests de pipeline dominio ─────────────────────────────────────────────────

def test_m2_example_genera_gap_jornada():
    """El contrato de HG (48h) genera gap de jornada con cita en el span correcto."""
    gaps = detect_gaps(M2_EXAMPLE_RECORD, reference_date=REF)
    g1 = next((g for g in gaps if g.gap_id == "g1"), None)
    assert g1 is not None
    assert g1.severity == "alta"
    assert g1.source_field == "weekly_hours"


def test_m2_example_genera_gap_contrato_vencido():
    """El contrato (end=2025-01-31) ya vencio → g4 con mensaje de 'VENCIDO'."""
    gaps = detect_gaps(M2_EXAMPLE_RECORD, reference_date=REF)
    g4 = next((g for g in gaps if g.gap_id == "g4"), None)
    assert g4 is not None
    assert g4.severity == "alta"
    assert "VENCIDO" in g4.issue


def test_m2_example_no_genera_reclasificacion():
    """termino_fijo no es prestacion_servicios → no debe haber g2."""
    gaps = detect_gaps(M2_EXAMPLE_RECORD, reference_date=REF)
    assert all(g.gap_id != "g2" for g in gaps)


def test_m2_example_source_llega_al_gap_via_service():
    """
    Trazabilidad completa: el span del documento (extraido por M2)
    llega al gap de M3 para que M5 pueda citarlo en el otrosí.
    """
    svc = ComplianceService(AuditLog())
    result = svc.analyze(CTX, "contrato-001", M2_EXAMPLE_RECORD, "contrato")

    g1 = next((g for g in result["gaps"] if g["gap_id"] == "g1"), None)
    assert g1 is not None
    assert g1["source"] is not None, "El span de weekly_hours debe llegar al gap"
    assert g1["source"]["span_start"] == 980
    assert g1["source"]["text"] == "jornada de cuarenta y ocho horas"


# ── Test de pipeline HTTP (M2 output como input del endpoint M3) ──────────────

def test_pipeline_http_m2_output_a_m3_endpoint():
    """
    Simula el flujo real via HTTP:
    - Input: response_example de M2 en contracts.json (serializado como JSON)
    - Output: gaps detectados por M3
    """
    resp = client.post(
        "/api/compliance/analyze",
        headers=AUTH,
        json={
            "doc_id": "contrato-001",
            "doc_type": "contrato",
            "record": {
                "doc_id": "contrato-001",
                "vinculo_type": {
                    "value": "termino_fijo",
                    "source": {"span_start": 340, "span_end": 372,
                               "text": "contrato a termino fijo de un (1) ano",
                               "confidence": 0.95, "doc_id": "contrato-001"},
                    "status": "ok",
                },
                "base_salary": {
                    "value": {"value": 2500000, "currency": "COP", "periodicity": "mensual"},
                    "source": {"span_start": 1820, "span_end": 1875,
                               "text": "salario mensual de DOS MILLONES QUINIENTOS MIL PESOS",
                               "confidence": 0.98, "doc_id": "contrato-001"},
                    "status": "ok",
                },
                "start_date": {
                    "value": "2024-02-01",
                    "source": {"span_start": 410, "span_end": 440,
                               "text": "a partir del 1 de febrero de 2024",
                               "confidence": 0.96, "doc_id": "contrato-001"},
                    "status": "ok",
                },
                "end_date": {
                    "value": "2025-01-31",
                    "source": {"span_start": 442, "span_end": 470,
                               "text": "hasta el 31 de enero de 2025",
                               "confidence": 0.94, "doc_id": "contrato-001"},
                    "status": "ok",
                },
                "weekly_hours": {
                    "value": 48,
                    "source": {"span_start": 980, "span_end": 1010,
                               "text": "jornada de cuarenta y ocho horas",
                               "confidence": 0.9, "doc_id": "contrato-001"},
                    "status": "ok",
                },
                "role": {
                    "value": "Asesor comercial",
                    "source": {"span_start": 250, "span_end": 280,
                               "text": "cargo de Asesor comercial",
                               "confidence": 0.92, "doc_id": "contrato-001"},
                    "status": "ok",
                },
                "employer": {
                    "value": {"name": "Empresa Cliente SAS", "nit": "900123456-7"},
                    "source": None, "status": "ok",
                },
                "empleado_nombre": {
                    "value": "Trabajador HG",
                    "source": {"span_start": 150, "span_end": 170,
                               "text": "el Trabajador HG",
                               "confidence": 0.9, "doc_id": "contrato-001"},
                    "status": "ok",
                },
                "empleado_documento": {
                    "value": "79.123.456",
                    "source": {"span_start": 175, "span_end": 195,
                               "text": "CC 79.123.456",
                               "confidence": 0.9, "doc_id": "contrato-001"},
                    "status": "ok",
                },
                "auxilio_transporte": {"value": None, "source": None, "status": "not_found"},
                "salario_variable": {"value": False, "source": None, "status": "ok"},
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    gap_ids = [g["gap_id"] for g in body["gaps"]]
    assert "g1" in gap_ids, "El contrato de HG debe tener gap de jornada"
    assert "g4" in gap_ids, "El contrato de HG vencido debe tener gap de vencimiento"
    assert "g2" not in gap_ids, "termino_fijo no debe generar reclasificacion"


# ── Stress test de determinismo ───────────────────────────────────────────────

def test_stress_determinismo_1000_llamadas():
    """
    Misma entrada, 1000 llamadas → resultado identico.
    Confirma que no hay estado mutable oculto ni dependencia de reloj.
    """
    expected = detect_gaps(M2_EXAMPLE_RECORD, reference_date=REF)
    for i in range(1000):
        result = detect_gaps(M2_EXAMPLE_RECORD, reference_date=REF)
        assert result == expected, f"Resultado distinto en iteracion {i}: {result}"


# ── Tenant isolation ──────────────────────────────────────────────────────────

def test_tenant_isolation_mismos_gaps_diferentes_tenants():
    """
    Dos tenants distintos analizando el mismo contrato → mismos gaps.
    No debe haber contaminacion de datos entre tenants.
    """
    ctx_a = TenantContext(tenant_id="empresa-a", actor="runner")
    ctx_b = TenantContext(tenant_id="empresa-b", actor="runner")

    audit_a = AuditLog()
    audit_b = AuditLog()

    result_a = ComplianceService(audit_a).analyze(ctx_a, "doc-001", M2_EXAMPLE_RECORD, "contrato")
    result_b = ComplianceService(audit_b).analyze(ctx_b, "doc-001", M2_EXAMPLE_RECORD, "contrato")

    assert result_a["gaps"] == result_b["gaps"], "Gaps deben ser identicos entre tenants"

    # El audit de cada tenant solo tiene sus propias entradas
    assert all(e.tenant_id == "empresa-a" for e in audit_a.for_tenant("empresa-a"))
    assert all(e.tenant_id == "empresa-b" for e in audit_b.for_tenant("empresa-b"))
    assert audit_a.for_tenant("empresa-b") == []
    assert audit_b.for_tenant("empresa-a") == []


# ── Edge cases con datos reales ───────────────────────────────────────────────

def test_contrato_vencido_mensaje_no_dice_dias_negativos():
    """Contrato vencido → issue dice 'VENCIDO hace X dias', no 'vence en -X dias'."""
    gaps = detect_gaps(M2_EXAMPLE_RECORD, reference_date=REF)
    g4 = next((g for g in gaps if g.gap_id == "g4"), None)
    assert g4 is not None
    assert "-" not in g4.issue, f"El issue no debe tener dias negativos: '{g4.issue}'"
    assert "VENCIDO" in g4.issue


def test_contrato_termino_fijo_futuro_no_vencido_mensaje_correcto():
    """Contrato que vence en 13 dias → mensaje 'vence en 13 dias', no 'VENCIDO'."""
    from app.domain.models import Field as F
    rec = M2_EXAMPLE_RECORD.model_copy(update={
        "end_date": F(value="2026-07-01", source=None, status="ok"),
    })
    gaps = detect_gaps(rec, reference_date=REF)
    g4 = next((g for g in gaps if g.gap_id == "g4"), None)
    assert g4 is not None
    assert "VENCIDO" not in g4.issue
    assert "13" in g4.issue or "vence en" in g4.issue
