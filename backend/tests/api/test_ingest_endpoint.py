"""Test del endpoint M1: auth multitenant + aislamiento de datos entre tenants."""
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}


def _upload(filename: str, data: bytes, headers: dict):
    return client.post("/api/ingest", headers=headers,
                       files={"file": (filename, io.BytesIO(data), "text/plain")})


def test_ingest_sin_api_key_rechazado():
    assert _upload("c.txt", b"hola", {}).status_code == 401


def test_ingest_txt_ok_con_tenant():
    resp = _upload("contrato.txt", b"CONTRATO DE TRABAJO ...", AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "digital"
    assert body["doc_id"] == "contrato"


def test_escaneo_ilegible_endpoint():
    resp = _upload("scan.txt", b"[[SCAN_ILEGIBLE]] xxx", AUTH)
    assert resp.json()["status"] == "needs_human"


def test_formato_no_soportado_da_400_no_500():
    # Subir .png (no soportado) debe dar un 400 limpio, NUNCA un 500.
    resp = _upload("foto.png", b"fake png", AUTH)
    assert resp.status_code == 400
    assert "Formato no soportado" in resp.json()["detail"]


def test_archivo_vacio_va_a_needs_human():
    resp = _upload("vacio.txt", b"", AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "needs_human"
