"""
Endpoints del Motor 2 con el contrato que consume el frontend: estado de diligencia
de 5 puntos → guardián de 7 garantías (adaptado) → respuesta nullity/can_proceed/
missing_steps[].citation, y 3 documentos con body_markdown.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}

# Estado completo (los 5 puntos en True) → CONFORME.
_OK = {
    "worker_notified_right_to_companion": True,
    "charges_read": True,
    "evidence_presented": True,
    "worker_allowed_to_respond": True,
    "term_respected": True,
}
# Falta dar oportunidad de descargos → NULO (garantía ALTA).
_NULO = {**_OK, "worker_allowed_to_respond": False}


def test_guardian_conforme_puede_proceder():
    r = client.post("/api/disciplinary/guardian", headers=AUTH,
                    json={"session_id": "s1", "diligence_state": _OK})
    assert r.status_code == 200
    b = r.json()
    assert b["can_proceed"] is True
    assert b["nullity_alert"] is False
    assert b["missing_steps"] == []


def test_guardian_nulo_lista_pasos_con_citacion():
    r = client.post("/api/disciplinary/guardian", headers=AUTH,
                    json={"session_id": "s1", "diligence_state": _NULO})
    b = r.json()
    assert b["nullity_alert"] is True and b["can_proceed"] is False
    assert b["missing_steps"]
    cita = b["missing_steps"][0]["citation"]
    assert cita["verified"] is True and "art" in cita["article"]


def test_guardian_requiere_api_key():
    assert client.post("/api/disciplinary/guardian",
                       json={"session_id": "s1", "diligence_state": _OK}).status_code == 401


def test_documents_emite_3_docs():
    r = client.post("/api/disciplinary/documents", headers=AUTH,
                    json={"session_id": "s1", "diligence_state": _OK, "transcript": "el trabajador aceptó"})
    assert r.status_code == 200
    docs = {d["type"]: d for d in r.json()["documents"]}
    assert set(docs) == {"citacion_descargos", "acta_descargos", "decision_final"}
    assert all(d["body_markdown"] for d in docs.values())
    assert docs["decision_final"]["blocked_if_nullity"] is True


def test_documents_decision_bloqueada_si_nulo_pero_emite_los_3():
    r = client.post("/api/disciplinary/documents", headers=AUTH,
                    json={"session_id": "s1", "diligence_state": _NULO, "transcript": ""})
    assert r.status_code == 200
    docs = {d["type"]: d for d in r.json()["documents"]}
    assert "BLOQUEADA" in docs["decision_final"]["body_markdown"]
    assert docs["citacion_descargos"]["body_markdown"]   # la citación sí se emite
