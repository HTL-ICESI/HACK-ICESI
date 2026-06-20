"""
Tests M5 — Generador de subsanación.

Criterios de aceptación (brief M5):
  1. Otrosí g1 → body con '42' + cita Ley 2101.
  2. Cifra manipulada ≠ motor → BlockedOutput (documento NO se devuelve).
  3. validate_figures determinista (mismo input → mismo veredicto).
  4. Router POST /api/remediation/generate → shape contracts.json M5.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from app.core.errors import BlockedOutput
from app.core.tenancy import TenantContext
from app.domain.remediation.validator import validate_figures
from app.services.remediation_service import RemediationService

CTX = TenantContext(tenant_id="empresa-001", actor="test")

G1_GAP = {
    "gap_id": "g1",
    "issue": "Jornada de 48h excede el máximo legal de 42h (Ley 2101/2021)",
    "severity": "alta",
    "norm": "Ley 2101/2021 art. 3",
    "remedy_type": "otrosi",
}


# ─── Test 1: otrosí g1 genera documento con "42" y cita Ley 2101 ─────────────

@pytest.mark.asyncio
async def test_otrosi_g1_genera_con_42_y_cita_ley_2101():
    """
    El LLM devuelve un cuerpo correcto con '42 horas semanales'.
    El documento debe salir sin bloqueo y con la cita de Ley 2101/2021.
    """
    llm = AsyncMock()
    llm.draft_document.return_value = (
        "## Otrosí No. 1 — Ajuste de Jornada\n\n"
        "...se modifica la jornada a CUARENTA Y DOS (42) horas semanales, "
        "conforme a la Ley 2101 de 2021, artículo 3..."
    )

    svc = RemediationService(llm)
    result = await svc.generate(CTX, "contrato-001", G1_GAP, None, "otrosi")

    # Figura "42" presente en el documento
    assert "42" in result["body_markdown"]

    # No bloqueado
    assert result["validation"]["blocked"] is False
    assert result["validation"]["figures_match_engine"] is True

    # Cita de Ley 2101/2021 art. 3 en las citations
    norm_ids = {c.get("norm_id", "") for c in result["citations"]}
    assert "Ley 2101/2021" in norm_ids, f"Cita Ley 2101 no encontrada. citations={result['citations']}"

    # Shape básica de M5 (contracts.json)
    assert result["doc_id"] == "contrato-001"
    assert result["document_type"] == "otrosi"
    assert "42" in result["title"]
    assert result["figures_used"][0]["label"] == "jornada_nueva"
    assert result["figures_used"][0]["value"] == 42


# ─── Test 2: cifra manipulada → BlockedOutput ────────────────────────────────

@pytest.mark.asyncio
async def test_cifra_manipulada_bloquea_documento():
    """
    Si el LLM devuelve un cuerpo con la cifra incorrecta (48 en vez de 42),
    el service lanza BlockedOutput y NO devuelve el documento.
    """
    llm = AsyncMock()
    llm.draft_document.return_value = (
        "## Otrosí (MANIPULADO)\n\n"
        "...jornada de CUARENTA Y OCHO (48) horas semanales..."
        # "42" ausente → validate_figures falla
    )

    svc = RemediationService(llm)
    with pytest.raises(BlockedOutput):
        await svc.generate(CTX, "contrato-001", G1_GAP, None, "otrosi")


# ─── Test 3: determinismo del validador ──────────────────────────────────────

def test_validate_figures_es_determinista():
    """
    validate_figures: mismo input → mismo veredicto, sin estado interno.
    Función pura: safe para paralelismo y auditoría.
    """
    body_ok = "...jornada a CUARENTA Y DOS (42) horas semanales, Ley 2101 de 2021..."
    body_wrong = "...jornada de CUARENTA Y OCHO (48) horas semanales..."
    figures = {"jornada_nueva": 42}

    # True siempre que "42" esté presente
    assert validate_figures(body_ok, figures) is True
    assert validate_figures(body_ok, figures) is True   # segunda llamada idéntica

    # False siempre que "42" esté ausente
    assert validate_figures(body_wrong, figures) is False
    assert validate_figures(body_wrong, figures) is False


def test_validate_figures_float_normaliza_a_entero():
    """42.0 debe tratarse como '42' al buscar en el texto."""
    body = "jornada de 42 horas"
    assert validate_figures(body, {"jornada_nueva": 42.0}) is True


def test_validate_figures_vacio_siempre_pasa():
    """Sin figuras que verificar → el documento pasa (no hay cifras que validar)."""
    assert validate_figures("cualquier texto", {}) is True


# ─── Test 4: degradación honesta (sin LLM → skeleton pasa validate_figures) ─

@pytest.mark.asyncio
async def test_degradacion_sin_llm_usa_skeleton():
    """
    Cuando el LLM no está disponible, draft_document devuelve el skeleton.
    El skeleton ya tiene '42' inyectado → validate_figures pasa y el
    documento se devuelve sin bloqueo.
    """
    llm = AsyncMock()
    # Simula la degradación honesta del adapter: devuelve el skeleton directamente
    async def _passthrough(kind, context):
        return context["skeleton"]

    llm.draft_document.side_effect = _passthrough

    svc = RemediationService(llm)
    result = await svc.generate(CTX, "contrato-001", G1_GAP, None, "otrosi")

    assert "42" in result["body_markdown"]
    assert result["validation"]["blocked"] is False


# ─── Test 5: router integración ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_router_generate_endpoint():
    """POST /api/remediation/generate → 200 con shape de contracts.json M5."""
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.main import app

    good_body = (
        "## Otrosí\n\n"
        "...jornada a CUARENTA Y DOS (42) horas semanales, Ley 2101 de 2021..."
    )

    async def _mock_generate(ctx, doc_id, gap_data, liquidation_data, doc_type, record=None):
        return {
            "doc_id": doc_id,
            "document_type": doc_type,
            "title": "Otrosí No. 1 — Ajuste de jornada laboral a 42 horas",
            "body_markdown": good_body,
            "figures_used": [{"label": "jornada_nueva", "value": 42, "source": "M3.gap.g1"}],
            "citations": [{"norm_id": "Ley 2101/2021", "article": "art. 3",
                           "title": "Reduccion jornada a 42h", "url": "https://...", "verified": False}],
            "validation": {"figures_match_engine": True, "blocked": False},
        }

    with patch("app.api.deps.remediation_service.generate", side_effect=_mock_generate):
        client = TestClient(app)
        resp = client.post(
            "/api/remediation/generate",
            json={"doc_id": "contrato-001", "gap": G1_GAP, "doc_type": "otrosi"},
            headers={"Authorization": "Bearer demo-hg-key"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["document_type"] == "otrosi"
    assert data["validation"]["blocked"] is False
    assert "42" in data["body_markdown"]


# ─── Test 6: g4 con M4 no lanza BlockedOutput (ADR-M5-002) ──────────────────

@pytest.mark.asyncio
async def test_g4_con_m4_no_lanza_blocked():
    """
    Regresión ADR-M5-002: g4 + liquidation_data de M4 no debe lanzar BlockedOutput.
    build_figures filtra las claves de M4 a solo las referenciadas en el skeleton;
    validate_figures verifica las cifras formateadas (COP '1.000.000') en el body.
    """
    import dataclasses
    from app.domain.liquidation.engine import LiquidationInput, liquidate
    from app.domain.models import Field, FieldStatus, Money, Periodicity

    G4_GAP = {
        "gap_id": "g4",
        "issue": "Contrato a termino fijo VENCIDO hace 180 dias",
        "severity": "alta",
        "norm_id": "CST",
        "article": "art. 46",
        "remedy_type": "acta_terminacion",
    }

    liq = dataclasses.asdict(
        liquidate(LiquidationInput(salario_basico=2_000_000, days_worked=180, vinculo_type="termino_fijo"))
    )

    llm = AsyncMock()
    async def passthrough(kind, ctx): return ctx["skeleton"]
    llm.draft_document.side_effect = passthrough

    svc = RemediationService(llm)
    result = await svc.generate(CTX, "contrato-tf", G4_GAP, liq, "acta_terminacion")

    assert result["validation"]["blocked"] is False
    body = result["body_markdown"]
    # Montos de M4 deben aparecer formateados en el acta
    assert "1.000.000" in body, f"cesantias '1.000.000' ausente. body={body[:200]}"
    assert "Cesantías" in body


# ─── Test 8: skeleton personalizado con datos de partes (ADR-M5-001) ─────────

@pytest.mark.asyncio
async def test_skeleton_incluye_datos_de_partes():
    """
    Cuando se pasa el DocumentRecord, el documento debe contener
    el nombre del empleador, el trabajador, el cargo y la C.C.
    Valida ADR-M5-001: party_data inyectado por código antes del LLM.
    """
    from app.domain.models import (
        DocumentRecord, Field, Source, FieldStatus, Money, Periodicity
    )

    def _ok_field(value):
        return Field(value=value, source=None, status=FieldStatus.OK)

    record = DocumentRecord(
        doc_id="contrato-001",
        employer=Field(
            value={"name": "HURTADO GANDINI ABOGADOS SAS", "nit": "901.234.567-8"},
            source=None, status=FieldStatus.OK,
        ),
        empleado_nombre=_ok_field("JOSE ANDRES OSPINO"),
        empleado_documento=_ok_field("1144000000"),
        role=_ok_field("Vendedor"),
        vinculo_type=_ok_field("termino_indefinido"),
        base_salary=Field(
            value=Money(value=1_750_905, currency="COP", periodicity=Periodicity.MENSUAL),
            source=None, status=FieldStatus.OK,
        ),
        auxilio_transporte=Field(value=None, source=None, status=FieldStatus.NOT_FOUND),
        salario_variable=_ok_field(True),
        start_date=_ok_field("2026-01-01"),
        end_date=Field(value=None, source=None, status=FieldStatus.NOT_FOUND),
        weekly_hours=_ok_field(48),
    )

    # LLM pasa el skeleton tal cual (degradación honesta)
    llm = AsyncMock()
    async def _passthrough(kind, context):
        return context["skeleton"]
    llm.draft_document.side_effect = _passthrough

    svc = RemediationService(llm)
    result = await svc.generate(CTX, "contrato-001", G1_GAP, None, "otrosi", record)

    body = result["body_markdown"]
    assert "HURTADO GANDINI ABOGADOS SAS" in body,   "Falta nombre del empleador"
    assert "JOSE ANDRES OSPINO" in body,              "Falta nombre del trabajador"
    assert "901.234.567-8" in body,                   "Falta NIT"
    assert "1144000000" in body,                      "Falta cédula"
    assert "Vendedor" in body,                        "Falta cargo"
    assert "42" in body,                              "Falta cifra de jornada"
    assert result["validation"]["blocked"] is False
