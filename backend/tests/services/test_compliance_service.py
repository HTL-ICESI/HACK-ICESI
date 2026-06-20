"""
Tests del ComplianceService (M3) — capa de servicio.

Verifica:
1. Anti-alucinacion: si la norma NO esta en el corpus, el gap NO se emite.
2. Resolucion de citas: el gap emitido tiene la Citation correcta del corpus.
3. Source propagation: el span del campo del documento llega al gap de salida.
4. applicable_norms siempre presentes (CST art.64 y art.65).
5. Aislamiento de tenant: el audit trail registra el tenant correcto.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest

from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.domain.models import DocumentRecord, Field, Source
from app.services.compliance_service import ComplianceService

# Tenant y servicio de prueba
CTX = TenantContext(tenant_id="empresa-test", actor="test-runner")
REF = date(2026, 6, 18)


def _svc() -> ComplianceService:
    return ComplianceService(AuditLog())


def _record(
    *,
    vinculo: str = "termino_indefinido",
    hours: float = 42,
    start: str = "2026-06-01",
    end: str | None = None,
    hours_source: Source | None = None,
) -> DocumentRecord:
    return DocumentRecord(
        doc_id="svc-test-001",
        vinculo_type=Field(value=vinculo),
        base_salary=Field(value={"value": 2_500_000, "currency": "COP", "periodicity": "mensual"}),
        start_date=Field(value=start),
        end_date=Field(value=end),
        weekly_hours=Field(value=hours, source=hours_source),
        role=Field(value="Asesor"),
        employer=Field(value={"name": "Empresa SAS"}),
        empleado_nombre=Field(value="Trabajador Test"),
        empleado_documento=Field(value="79.000.000"),
        auxilio_transporte=Field(value=None, status="not_found"),
        salario_variable=Field(value=False),
    )


# ── 1. Anti-alucinacion ───────────────────────────────────────────────────────

def test_antialucinacion_norma_sin_nodo_no_emite_gap():
    """
    REGLA DE ORO: si resolve() devuelve None (norma no en corpus),
    el gap NO aparece en la respuesta. Nunca se afirma un gap sin fuente.
    """
    rec = _record(hours=48)  # generaria g1 en dominio

    with patch("app.services.compliance_service.resolve", return_value=None):
        result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")

    assert result["gaps"] == [], (
        "Un gap sin nodo en corpus NO debe aparecer en la respuesta"
    )
    assert result["applicable_norms"] == [], (
        "applicable_norms tampoco se emiten sin nodo en corpus"
    )


def test_antialucinacion_norma_parcialmente_presente():
    """
    Si solo ALGUNAS normas estan en el corpus, solo esos gaps se emiten.
    El resto se descarta silenciosamente.
    """
    rec = _record(hours=48, vinculo="prestacion_servicios")
    # Solo devolvemos nodo para Ley 2101 (g1), no para Ley 2466 (g2)
    corpus_parcial = {
        "Ley 2101/2021:art. 3": {
            "norm_id": "Ley 2101/2021", "article": "art. 3",
            "title": "Reduccion jornada a 42h", "url": "https://...", "verified": False,
        }
    }

    def resolve_parcial(norm_id: str, article: str) -> dict | None:
        return corpus_parcial.get(f"{norm_id}:{article}")

    with patch("app.services.compliance_service.resolve", side_effect=resolve_parcial):
        result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")

    gap_ids = [g["gap_id"] for g in result["gaps"]]
    assert "g1" in gap_ids, "g1 debe aparecer (norma presente en corpus)"
    assert "g2" not in gap_ids, "g2 NO debe aparecer (norma ausente del corpus)"


# ── 2. Resolucion de citas ────────────────────────────────────────────────────

def test_citation_se_resuelve_correctamente_desde_corpus():
    """El gap emitido debe tener la Citation con los campos exactos del corpus."""
    rec = _record(hours=48)
    result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")

    gaps = {g["gap_id"]: g for g in result["gaps"]}
    assert "g1" in gaps, "Con jornada 48h debe aparecer g1"

    cit = gaps["g1"]["citation"]
    assert cit["norm_id"] == "Ley 2101/2021"
    assert cit["article"] == "art. 3"
    assert "42h" in cit["title"] or "jornada" in cit["title"].lower()
    assert isinstance(cit["verified"], bool)


def test_gap_reclasificacion_citation_ley_2466():
    """g2 reclasificacion cita exactamente Ley 2466/2025 art. 5."""
    rec = _record(vinculo="prestacion_servicios")
    result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")

    gaps = {g["gap_id"]: g for g in result["gaps"]}
    assert "g2" in gaps
    cit = gaps["g2"]["citation"]
    assert cit["norm_id"] == "Ley 2466/2025"
    assert cit["article"] == "art. 5"
    assert gaps["g2"]["remedy_type"] == "contrato_corregido"


# ── 3. Propagacion del Source (trazabilidad) ─────────────────────────────────

def test_source_del_campo_llega_al_gap():
    """
    Si el campo que disparo el gap tiene un Source (span en el documento),
    ese span debe aparecer en la salida del gap para trazabilidad completa.
    """
    span = Source(
        span_start=980, span_end=1010,
        text="jornada de cuarenta y ocho horas",
        confidence=0.9, doc_id="contrato-001",
    )
    rec = _record(hours=48, hours_source=span)
    result = _svc().analyze(CTX, "contrato-001", rec, "contrato")

    gaps = {g["gap_id"]: g for g in result["gaps"]}
    assert "g1" in gaps
    src = gaps["g1"]["source"]
    assert src is not None, "g1 debe traer el source del campo weekly_hours"
    assert src["span_start"] == 980
    assert src["span_end"] == 1010
    assert src["text"] == "jornada de cuarenta y ocho horas"
    assert src["confidence"] == pytest.approx(0.9)


def test_gap_sin_source_en_campo_emite_source_null():
    """Si el campo no tiene span (extraccion por LLM sin cita), source del gap es null."""
    rec = _record(hours=48)  # hours_source=None por defecto
    result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")

    gaps = {g["gap_id"]: g for g in result["gaps"]}
    assert gaps["g1"]["source"] is None


# ── 4. applicable_norms siempre presentes ────────────────────────────────────

def test_applicable_norms_incluye_cst_64_y_65():
    """CST art.64 (indemnizacion) y art.65 (mora) son normas de referencia siempre presentes."""
    rec = _record()  # contrato conforme
    result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")

    norm_ids = {(n["norm_id"], n["article"]) for n in result["applicable_norms"]}
    assert ("CST", "art. 64") in norm_ids
    assert ("CST", "art. 65") in norm_ids


# ── 5. Forma de respuesta (shape exacta del contrato M3) ─────────────────────

def test_response_shape_cumple_contrato_m3():
    """La respuesta tiene exactamente los campos especificados en contracts.json M3."""
    rec = _record(hours=48)
    result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")

    # Top-level
    assert "doc_id" in result
    assert "gaps" in result
    assert "applicable_norms" in result

    # Cada gap
    for gap in result["gaps"]:
        assert "gap_id" in gap
        assert "issue" in gap
        assert "severity" in gap
        assert "citation" in gap
        assert "source" in gap         # puede ser null, pero la key debe existir
        assert "remedy_type" in gap
        # Citation
        cit = gap["citation"]
        assert "norm_id" in cit
        assert "article" in cit
        assert "title" in cit
        assert "url" in cit
        assert "verified" in cit


def test_severity_solo_valores_validos():
    """severity solo puede ser 'alta', 'media' o 'baja'."""
    rec = _record(hours=48, vinculo="prestacion_servicios", start="2024-01-01")
    result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")
    valid = {"alta", "media", "baja"}
    for gap in result["gaps"]:
        assert gap["severity"] in valid, f"severity invalida: {gap['severity']}"


def test_remedy_type_solo_valores_validos():
    """remedy_type solo puede ser uno de los 4 valores del contrato."""
    rec = _record(hours=48, vinculo="prestacion_servicios", start="2024-01-01")
    result = _svc().analyze(CTX, "svc-test-001", rec, "contrato")
    valid = {"otrosi", "instruccion_nomina", "acta_terminacion", "contrato_corregido"}
    for gap in result["gaps"]:
        assert gap["remedy_type"] in valid, f"remedy_type invalido: {gap['remedy_type']}"


# ── 6. Audit trail ───────────────────────────────────────────────────────────

def test_audit_registra_tenant_correcto():
    """Cada llamada a analyze() debe quedar en el audit log del tenant correcto."""
    audit = AuditLog()
    svc = ComplianceService(audit)
    rec = _record(hours=48)

    svc.analyze(CTX, "svc-test-001", rec, "contrato")

    entries = audit.for_tenant("empresa-test")
    assert len(entries) == 1
    assert entries[0].action == "compliance.analyze"
    assert entries[0].ref == "svc-test-001"


def test_audit_grounding_contiene_normas_de_gaps_emitidos():
    """El grounding del audit debe listar las normas de los gaps que se emitieron."""
    audit = AuditLog()
    svc = ComplianceService(audit)
    rec = _record(hours=48)

    svc.analyze(CTX, "svc-test-001", rec, "contrato")

    entry = audit.for_tenant("empresa-test")[0]
    assert "Ley 2101/2021" in entry.grounding
