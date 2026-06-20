"""
Tests del endpoint POST /api/compliance/analyze — M3.

Verifica el contrato HTTP completo: auth, shape de request/response,
y el isolation test del contrato M3: "sin fuente citable no emite el gap".
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _record_json(
    *,
    vinculo: str = "termino_indefinido",
    hours: float = 42,
    start: str = "2026-06-01",
    end: str | None = None,
) -> dict:
    """DocumentRecord minimo serializado como JSON para el endpoint."""
    return {
        "doc_id": "ep-test-001",
        "vinculo_type": {"value": vinculo, "source": None, "status": "ok"},
        "base_salary": {
            "value": {"value": 2_500_000, "currency": "COP", "periodicity": "mensual"},
            "source": None, "status": "ok",
        },
        "start_date": {"value": start, "source": None, "status": "ok"},
        "end_date": {"value": end, "source": None, "status": "ok"},
        "weekly_hours": {"value": hours, "source": None, "status": "ok"},
        "role": {"value": "Asesor comercial", "source": None, "status": "ok"},
        "employer": {"value": {"name": "Empresa Cliente SAS"}, "source": None, "status": "ok"},
        "empleado_nombre": {"value": "Trabajador Test", "source": None, "status": "ok"},
        "empleado_documento": {"value": "79.000.000", "source": None, "status": "ok"},
        "auxilio_transporte": {"value": None, "source": None, "status": "not_found"},
        "salario_variable": {"value": False, "source": None, "status": "ok"},
    }


def _analyze(record: dict, doc_type: str = "contrato", headers: dict = AUTH) -> dict:
    resp = client.post(
        "/api/compliance/analyze",
        headers=headers,
        json={"doc_id": "ep-test-001", "record": record, "doc_type": doc_type},
    )
    return resp


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_analyze_sin_auth_rechazado():
    """Sin Authorization -> 401, no se procesa nada."""
    resp = _analyze(_record_json(), headers={})
    assert resp.status_code == 401


# ── Happy path ────────────────────────────────────────────────────────────────

def test_analyze_contrato_conforme_200_cero_gaps():
    """Contrato conforme (42h, indefinido, reciente) -> 200, gaps vacia."""
    resp = _analyze(_record_json(hours=42, vinculo="termino_indefinido", start="2026-06-10"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["doc_id"] == "ep-test-001"
    assert body["gaps"] == []
    assert len(body["applicable_norms"]) >= 2   # CST 64 + 65 siempre presentes


def test_analyze_jornada_48h_retorna_gap_g1():
    """48h -> g1 en respuesta con citation Ley 2101 y remedy otrosi."""
    resp = _analyze(_record_json(hours=48, start="2026-06-10"))
    assert resp.status_code == 200
    gaps = {g["gap_id"]: g for g in resp.json()["gaps"]}
    assert "g1" in gaps
    assert gaps["g1"]["severity"] == "alta"
    assert gaps["g1"]["citation"]["norm_id"] == "Ley 2101/2021"
    assert gaps["g1"]["remedy_type"] == "otrosi"


def test_analyze_prestacion_servicios_retorna_gap_g2():
    """prestacion_servicios -> g2 con Ley 2466."""
    resp = _analyze(_record_json(vinculo="prestacion_servicios", start="2026-06-10"))
    assert resp.status_code == 200
    gaps = {g["gap_id"]: g for g in resp.json()["gaps"]}
    assert "g2" in gaps
    assert gaps["g2"]["citation"]["norm_id"] == "Ley 2466/2025"
    assert gaps["g2"]["remedy_type"] == "contrato_corregido"


def test_analyze_multiples_gaps_en_un_contrato():
    """Contrato con varias violaciones -> multiples gaps en una sola llamada."""
    # 48h + prestacion_servicios + inicio hace mas de 1 anio
    resp = _analyze(_record_json(
        vinculo="prestacion_servicios",
        hours=48,
        start="2024-01-01",
    ))
    assert resp.status_code == 200
    gap_ids = [g["gap_id"] for g in resp.json()["gaps"]]
    # Debe haber al menos g1 (jornada), g2 (reclasificacion), g3 (vacaciones)
    assert "g1" in gap_ids
    assert "g2" in gap_ids
    assert "g3" in gap_ids


def test_analyze_termino_fijo_proximo_a_vencer():
    """Termino fijo que vence en < 30 dias -> gap g4 alta."""
    resp = _analyze(_record_json(
        vinculo="termino_fijo",
        hours=42,
        start="2025-07-01",
        end="2026-07-01",   # 13 dias desde REF
    ))
    assert resp.status_code == 200
    gaps = {g["gap_id"]: g for g in resp.json()["gaps"]}
    assert "g4" in gaps
    assert gaps["g4"]["severity"] == "alta"
    assert gaps["g4"]["citation"]["norm_id"] == "CST"
    assert gaps["g4"]["citation"]["article"] == "art. 46"


# ── Isolation test del contrato M3 ───────────────────────────────────────────

def test_isolation_gaps_tienen_citation_con_campos_requeridos():
    """
    Isolation test: cada gap de la respuesta tiene una Citation verificable
    (norm_id, article, title, url, verified). Sin Citation -> gap no se emite.
    """
    resp = _analyze(_record_json(hours=48, vinculo="prestacion_servicios", start="2024-01-01"))
    assert resp.status_code == 200
    for gap in resp.json()["gaps"]:
        cit = gap.get("citation")
        assert cit is not None, f"Gap {gap['gap_id']} no tiene citation"
        assert cit.get("norm_id"), f"Gap {gap['gap_id']} tiene norm_id vacio"
        assert cit.get("article"), f"Gap {gap['gap_id']} tiene article vacio"
        assert cit.get("title"), f"Gap {gap['gap_id']} tiene title vacio"
        assert cit.get("url"), f"Gap {gap['gap_id']} tiene url vacio"
        assert isinstance(cit.get("verified"), bool)


def test_isolation_applicable_norms_siempre_presente():
    """applicable_norms esta en la respuesta incluso cuando no hay gaps."""
    resp = _analyze(_record_json(hours=42, start="2026-06-10"))
    assert resp.status_code == 200
    assert "applicable_norms" in resp.json()
    assert isinstance(resp.json()["applicable_norms"], list)


# ── Robustez de entrada ───────────────────────────────────────────────────────

def test_analyze_campos_null_no_explota():
    """Campos opcionales en null -> 200, no 500."""
    record = _record_json(hours=42, start="2026-06-10")
    record["end_date"] = {"value": None, "source": None, "status": "not_found"}
    record["role"] = {"value": None, "source": None, "status": "not_found"}
    resp = _analyze(record)
    assert resp.status_code == 200


def test_analyze_doc_type_rit_acepta_request():
    """doc_type='RIT' (no solo 'contrato') es valido y devuelve 200."""
    resp = _analyze(_record_json(hours=42, start="2026-06-10"), doc_type="RIT")
    assert resp.status_code == 200


def test_analyze_doc_id_en_respuesta_coincide_con_request():
    """El doc_id de la respuesta es el mismo que se envio en el request."""
    resp = _analyze(_record_json(hours=42, start="2026-06-10"))
    assert resp.json()["doc_id"] == "ep-test-001"
