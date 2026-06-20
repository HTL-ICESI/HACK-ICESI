"""
Tests HTTP del endpoint M4 (/api/liquidation/compute) — la ruta que consume el front.
Verifica que el caso gold real (José Ospino) sale correcto VÍA HTTP, no solo en el dominio.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}


def test_endpoint_gold_ospino_total_prestaciones_exacto():
    resp = client.post("/api/liquidation/compute", headers=AUTH, json={
        "doc_id": "gold-ospino",
        "monthly_salary": 1_750_905,
        "days_worked": 66,
        "vinculo_type": "termino_indefinido",
        "promedio_variable": 676_784.614,
        "auxilio_transporte": 249_095,
        "dias_pendientes_vacaciones": 9,
        "termination_cause": "renuncia",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["deterministic"] is True
    items = body["items"]
    assert items["total_prestaciones"] == pytest.approx(1_720_590.94, abs=0.5)
    assert items["indemnizacion"] == 0.0
    assert items["total"] == pytest.approx(1_720_590.94, abs=0.5)


def test_endpoint_sin_justa_causa_incluye_indemnizacion():
    resp = client.post("/api/liquidation/compute", headers=AUTH, json={
        "doc_id": "x",
        "monthly_salary": 1_750_905,
        "days_worked": 109,
        "vinculo_type": "termino_indefinido",
        "auxilio_transporte": 249_095,
        "termination_cause": "sin_justa_causa",
        "antiguedad_anios": 0.3,
    })
    assert resp.status_code == 200
    items = resp.json()["items"]
    # Caso gold 2 (hoja "formato"): prestaciones 1.498.180,53 + indemnización 1.750.905.
    assert items["total_prestaciones"] == pytest.approx(1_498_180.53, abs=0.5)
    assert items["indemnizacion"] == pytest.approx(1_750_905, abs=1)


def test_endpoint_requiere_api_key():
    resp = client.post("/api/liquidation/compute", json={
        "doc_id": "x", "monthly_salary": 1, "days_worked": 1, "vinculo_type": "termino_indefinido"})
    assert resp.status_code == 401
