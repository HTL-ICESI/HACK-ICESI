"""
Tests HTTP para GET /api/dashboard/exposure — M6.
Shape exacta del bloque M6 de contracts.json. Aislamiento multitenant.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}


def test_sin_auth_devuelve_401():
    resp = client.get("/api/dashboard/exposure", params={"company_id": "empresa-001"})
    assert resp.status_code == 401


def test_empresa_demo_devuelve_200_con_shape_correcta():
    resp = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["company_id"] == "empresa-001"
    assert "magic_number" in body
    assert "alerts" in body


def test_magic_number_tiene_todos_los_campos_requeridos():
    resp = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    mn = resp.json()["magic_number"]
    assert "outdated_clauses" in mn
    assert "pct_outdated" in mn
    assert "cop_exposure" in mn
    assert "exposure_formula" in mn
    assert "constants" in mn


def test_cop_exposure_es_50_trabajadores_por_smlmv():
    """50 * 1_423_500 + 0 reliquidaciones = 71_175_000 COP."""
    resp = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    mn = resp.json()["magic_number"]
    assert mn["cop_exposure"] == pytest.approx(50 * 1_423_500)


def test_pct_outdated_es_23_3():
    """7 de 30 cláusulas = 23.3%."""
    resp = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    mn = resp.json()["magic_number"]
    assert mn["pct_outdated"] == pytest.approx(23.3)
    assert mn["outdated_clauses"] == 7


def test_constants_incluye_smlmv_2026():
    resp = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    c = resp.json()["magic_number"]["constants"]
    assert c["SMLMV_2026"] == 1_423_500
    assert "mora_factor_art65" in c


def test_demo_emite_los_tres_tipos_de_alerta():
    """El dataset demo produce vencimiento + vacaciones + mora."""
    resp = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    types = {a["type"] for a in resp.json()["alerts"]}
    assert "vencimiento_contrato" in types
    assert "vacaciones_vencidas" in types
    assert "seguridad_social_mora" in types


def test_alerta_vencimiento_14_dias_es_alta():
    resp = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    venc = next((a for a in resp.json()["alerts"] if a["type"] == "vencimiento_contrato"), None)
    assert venc is not None
    assert venc["severity"] == "alta"
    assert venc["days_left"] == 14


def test_alerta_mora_tiene_monto_480k_cop():
    resp = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    mora = next((a for a in resp.json()["alerts"] if a["type"] == "seguridad_social_mora"), None)
    assert mora is not None
    assert mora["severity"] == "alta"
    assert mora["amount"]["value"] == 480_000.0
    assert mora["amount"]["currency"] == "COP"


def test_determinismo_dos_llamadas_identicas():
    """Mismo company_id → body idéntico (función pura)."""
    r1 = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    r2 = client.get("/api/dashboard/exposure", headers=AUTH, params={"company_id": "empresa-001"})
    assert r1.json() == r2.json()
