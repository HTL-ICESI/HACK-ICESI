"""
Test del endpoint M2 POST /api/extract: auth multitenant + shape del contrato.

Sin ANTHROPIC_API_KEY el adapter degrada honesto (campos blandos -> not_found),
pero los campos numéricos salen del regex determinista con su cita.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}

CONTRATO = (
    "El contrato regira a partir del 1 de febrero de 2024 hasta el 31 de enero "
    "de 2025. Jornada de 48 horas semanales. Salario mensual: 2.500.000 pesos."
)


def test_extract_sin_api_key_rechazado():
    r = client.post("/api/extract", json={"doc_id": "c", "text": "x"})
    assert r.status_code == 401


def test_extract_devuelve_shape_del_contrato():
    r = client.post("/api/extract", headers=AUTH,
                    json={"doc_id": "contrato-001", "text": CONTRATO})
    assert r.status_code == 200
    body = r.json()
    assert body["doc_id"] == "contrato-001"
    record = body["record"]
    # Las 7 claves del DocumentRecord, cada una como Field {value, source, status}.
    for key in ("vinculo_type", "base_salary", "start_date", "end_date",
                "weekly_hours", "role", "employer"):
        assert key in record
        assert set(record[key]) == {"value", "source", "status"}

    # Numéricos por regex -> con cita (source no nulo).
    salary = record["base_salary"]
    assert salary["status"] == "ok"
    assert salary["value"]["value"] == 2500000
    assert salary["source"] is not None
    assert record["weekly_hours"]["value"] == 48
    assert record["start_date"]["value"] == "2024-02-01"


def test_extract_texto_vacio_todos_campos_not_found():
    # Sin contenido ningún regex matchea → todo not_found, sin inventar nada.
    r = client.post("/api/extract", headers=AUTH,
                    json={"doc_id": "vacio-001", "text": ""})
    assert r.status_code == 200
    record = r.json()["record"]
    for key in ("vinculo_type", "base_salary", "start_date", "end_date",
                "weekly_hours", "role", "employer"):
        assert record[key]["status"] == "not_found"
        assert record[key]["value"] is None
        assert record[key]["source"] is None


def test_extract_body_sin_campo_text_error_422():
    # FastAPI debe rechazar el body si falta el campo requerido 'text'.
    r = client.post("/api/extract", headers=AUTH,
                    json={"doc_id": "solo-id"})
    assert r.status_code == 422


def test_extract_body_sin_campo_doc_id_error_422():
    r = client.post("/api/extract", headers=AUTH,
                    json={"text": "El contrato regira a partir del 1 de enero de 2025."})
    assert r.status_code == 422


def test_extract_source_doc_id_en_campos_numericos():
    # El source de los campos numéricos debe llevar el doc_id del request.
    r = client.post("/api/extract", headers=AUTH,
                    json={"doc_id": "contrato-ref-007", "text": CONTRATO})
    assert r.status_code == 200
    record = r.json()["record"]
    assert record["base_salary"]["source"]["doc_id"] == "contrato-ref-007"
    assert record["start_date"]["source"]["doc_id"] == "contrato-ref-007"


def test_extract_dos_llamadas_doc_ids_distintos():
    # Dos requests con doc_ids distintos devuelven sus propios records sin cruzarse.
    r1 = client.post("/api/extract", headers=AUTH,
                     json={"doc_id": "doc-A", "text": CONTRATO})
    r2 = client.post("/api/extract", headers=AUTH,
                     json={"doc_id": "doc-B", "text": CONTRATO})
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["doc_id"] == "doc-A"
    assert r2.json()["doc_id"] == "doc-B"


def test_extract_contrato_largo_con_palabras_y_numeros():
    # Texto con salario en palabras (como en contratos reales escaneados).
    texto = (
        "El contrato regira a partir del 01/03/2024 hasta el 28/02/2025. "
        "La trabajadora devengara un salario mensual de DOS MILLONES QUINIENTOS "
        "MIL PESOS. Cumplira una jornada de cuarenta y dos horas semanales "
        "conforme a la Ley 2101 de 2021."
    )
    r = client.post("/api/extract", headers=AUTH,
                    json={"doc_id": "palabras-001", "text": texto})
    assert r.status_code == 200
    record = r.json()["record"]

    assert record["base_salary"]["status"] == "ok"
    assert record["base_salary"]["value"]["value"] == 2_500_000
    assert record["start_date"]["value"] == "2024-03-01"
    assert record["end_date"]["value"] == "2025-02-28"
    assert record["weekly_hours"]["value"] == 42   # Ley 2101
