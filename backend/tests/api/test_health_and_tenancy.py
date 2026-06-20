"""Tests de la capa API: health + aislamiento multitenant (auth obligatoria)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    assert client.get("/health").json() == {"status": "ok"}


def test_endpoint_sin_api_key_rechazado():
    # Sin Authorization -> 401 (no se opera sin tenant)
    resp = client.post("/api/liquidation/compute", json={
        "doc_id": "x", "monthly_salary": 2_000_000, "days_worked": 360, "vinculo_type": "termino_indefinido"})
    assert resp.status_code == 401


def test_endpoint_con_api_key_demo_ok():
    resp = client.post("/api/liquidation/compute",
        headers={"Authorization": "Bearer demo-hg-key"},
        json={"doc_id": "x", "monthly_salary": 2_000_000, "days_worked": 360, "vinculo_type": "termino_indefinido"})
    assert resp.status_code == 200
    assert resp.json()["deterministic"] is True
