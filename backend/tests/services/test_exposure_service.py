"""
Tests de ExposureService (M6) — incluyendo la integración M3→M6 via from_m3_gaps().
"""
from datetime import date

import pytest

from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.services.exposure_service import ExposureRequest, ExposureService
from app.domain.exposure.alerts import ContractContext

CTX = TenantContext(tenant_id="empresa-001", actor="test-m6")
REF = date(2026, 6, 18)


def _svc() -> ExposureService:
    return ExposureService(AuditLog())


# ── from_m3_gaps: derivación automática desde output de M3 ────────────────────

def test_from_m3_gaps_deriva_workers_at_risk():
    """workers_at_risk = contratos con al menos 1 gap."""
    gap_results = [
        {"gaps": [{"gap_id": "g1", "severity": "alta"}]},   # con gaps
        {"gaps": []},                                         # sin gaps (conforme)
        {"gaps": [{"gap_id": "g2"}, {"gap_id": "g3"}]},     # con 2 gaps
    ]
    req = ExposureRequest.from_m3_gaps("empresa-001", gap_results)
    assert req.workers_at_risk == 2


def test_from_m3_gaps_deriva_outdated_clauses():
    """outdated_clauses = suma total de gaps en todos los contratos."""
    gap_results = [
        {"gaps": [{"gap_id": "g1"}]},
        {"gaps": [{"gap_id": "g1"}, {"gap_id": "g3"}]},
        {"gaps": []},
    ]
    req = ExposureRequest.from_m3_gaps("empresa-001", gap_results)
    assert req.outdated_clauses == 3


def test_from_m3_gaps_deriva_total_clauses_automaticamente():
    """total_clauses = len(gap_results) * _NUM_M3_RULES cuando no se pasa."""
    gap_results = [{"gaps": []}, {"gaps": []}, {"gaps": []}]
    req = ExposureRequest.from_m3_gaps("empresa-001", gap_results)
    assert req.total_clauses == 3 * 5  # 3 contratos × 5 reglas M3


def test_from_m3_gaps_sin_resultados_da_cero():
    req = ExposureRequest.from_m3_gaps("empresa-001", [])
    assert req.workers_at_risk == 0
    assert req.outdated_clauses == 0


def test_from_m3_gaps_todos_conformes_da_cero():
    gap_results = [{"gaps": []}, {"gaps": []}, {"gaps": []}]
    req = ExposureRequest.from_m3_gaps("empresa-001", gap_results)
    assert req.workers_at_risk == 0
    assert req.outdated_clauses == 0


# ── Integración M3 real → M6 con los casos gold sintéticos ───────────────────

def test_pipeline_m3_real_a_m6_gold_cases():
    """
    Corre los 3 contratos sintéticos por M3 y alimenta M6 con from_m3_gaps().
    Verifica que workers_at_risk y cop_exposure coincidan con los gaps reales.
    """
    from app.domain.models import DocumentRecord, Field, Source
    from app.services.compliance_service import ComplianceService

    compliance_svc = ComplianceService(AuditLog())

    # Contrato 1: 48h indefinido — g1(alta) + g3(media)
    r1 = DocumentRecord(
        doc_id="c1", vinculo_type=Field(value="termino_indefinido"),
        base_salary=Field(value={"value": 1_423_500, "currency": "COP", "periodicity": "mensual"}),
        start_date=Field(value="2025-01-01"), end_date=Field(value=None),
        weekly_hours=Field(value=48), role=Field(value="Auxiliar"),
        employer=Field(value={"name": "Empresa SAS"}),
        empleado_nombre=Field(value="Carlos"), empleado_documento=Field(value="1"),
        auxilio_transporte=Field(value=None, status="not_found"),
        salario_variable=Field(value=False),
    )
    # Contrato 2: prestacion_servicios 48h — g1+g2
    r2 = DocumentRecord(
        doc_id="c2", vinculo_type=Field(value="prestacion_servicios"),
        base_salary=Field(value={"value": 3_000_000, "currency": "COP", "periodicity": "mensual"}),
        start_date=Field(value="2025-01-01"), end_date=Field(value="2025-12-31"),
        weekly_hours=Field(value=48), role=Field(value="Desarrolladora"),
        employer=Field(value={"name": "TechValle SAS"}),
        empleado_nombre=Field(value="Ana"), empleado_documento=Field(value="2"),
        auxilio_transporte=Field(value=None, status="not_found"),
        salario_variable=Field(value=False),
    )
    # Contrato 3: conforme (42h, reciente) — 0 gaps
    r3 = DocumentRecord(
        doc_id="c3", vinculo_type=Field(value="termino_indefinido"),
        base_salary=Field(value={"value": 1_500_000, "currency": "COP", "periodicity": "mensual"}),
        start_date=Field(value="2026-06-01"), end_date=Field(value=None),
        weekly_hours=Field(value=42), role=Field(value="Analista"),
        employer=Field(value={"name": "Empresa SAS"}),
        empleado_nombre=Field(value="Pedro"), empleado_documento=Field(value="3"),
        auxilio_transporte=Field(value=None, status="not_found"),
        salario_variable=Field(value=False),
    )

    gap_results = [
        compliance_svc.analyze(CTX, r.doc_id, r, "contrato")
        for r in (r1, r2, r3)
    ]

    # r1: 2 gaps (g1+g3), r2: 2 gaps (g1+g2), r3: 0 gaps
    req = ExposureRequest.from_m3_gaps(
        "empresa-001", gap_results, reference_date=REF
    )

    assert req.workers_at_risk == 2        # r1 y r2 tienen gaps; r3 no
    assert req.outdated_clauses == 4       # g1+g3 + g1+g2 = 4 gaps
    assert req.total_clauses == 3 * 5     # 3 contratos × 5 reglas M3 (auto-derivado)

    result = _svc().compute(CTX, req)

    assert result["magic_number"]["cop_exposure"] == pytest.approx(2 * 1_423_500)
    assert result["magic_number"]["outdated_clauses"] == 4
    assert result["magic_number"]["pct_outdated"] == pytest.approx(4 / 15 * 100, rel=0.01)


# ── Determinismo ──────────────────────────────────────────────────────────────

def test_mismo_gap_results_mismo_cop():
    gap_results = [{"gaps": [{"gap_id": "g1"}]}, {"gaps": [{"gap_id": "g1"}, {"gap_id": "g3"}]}]
    req = ExposureRequest.from_m3_gaps("empresa-001", gap_results, reference_date=REF)
    r1 = _svc().compute(CTX, req)
    r2 = _svc().compute(CTX, req)
    assert r1["magic_number"]["cop_exposure"] == r2["magic_number"]["cop_exposure"]
