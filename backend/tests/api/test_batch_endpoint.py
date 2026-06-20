"""
Batch — procesamiento masivo. Offline (sin LLM): M2 regex + M3 reglas duras + M4
determinista corren igual; M5 degrada al esqueleto. Verifica ingest (ZIP y sueltos),
polling de status, result completo, aislamiento por tenant y robustez ante errores.
"""
import asyncio
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}
AUTH_B = {"Authorization": "Bearer demo-key-2"}

_C_48H = ("CONTRATO INDIVIDUAL DE TRABAJO A TERMINO INDEFINIDO\n"
          "Entre HG SAS y; y JUAN PEREZ, identificado con cedula de ciudadania numero 79.000.111,\n"
          "se celebra. Salario mensual de DOS MILLONES DE PESOS ($2.000.000).\n"
          "Jornada de cuarenta y ocho (48) horas semanales.\n"
          "Regira a partir del 1 de enero de 2024.\n")
_C_LIMPIO = ("CONTRATO INDIVIDUAL DE TRABAJO A TERMINO INDEFINIDO\n"
             "Entre HG SAS y; y MARIA GOMEZ, identificada con cedula de ciudadania numero 1.130.000.222,\n"
             "se celebra. Salario mensual de TRES MILLONES DE PESOS ($3.000.000).\n"
             "Jornada de cuarenta y dos (42) horas semanales.\n"
             "Regira a partir del 2 de enero de 2026.\n")


def _zip(*texts: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, t in enumerate(texts):
            z.writestr(f"contrato_{i+1}.txt", t)
    return buf.getvalue()


def _wait_done(batch_id: str, headers=AUTH, timeout=10.0) -> dict:
    """El procesamiento es async (create_task); el TestClient corre en el mismo loop,
    así que cedemos control hasta que termine."""
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = client.get(f"/api/batch/status/{batch_id}", headers=headers).json()
        if st["completed"] == st["total"]:
            return st
        time.sleep(0.2)
    return st


def test_ingest_zip_devuelve_batch_id_y_total():
    r = client.post("/api/batch/ingest", headers=AUTH,
                    files={"files": ("lote.zip", _zip(_C_48H, _C_LIMPIO), "application/zip")})
    assert r.status_code == 200
    b = r.json()
    assert b["total"] == 2 and len(b["batch_id"]) == 8


def test_pipeline_completa_y_summary_por_contrato():
    r = client.post("/api/batch/ingest", headers=AUTH,
                    files={"files": ("lote.zip", _zip(_C_48H, _C_LIMPIO), "application/zip")})
    st = _wait_done(r.json()["batch_id"])
    assert st["completed"] == 2
    by_name = {x["summary"]["worker_name"]: x for x in st["results"]}
    juan = by_name["JUAN PEREZ"]["summary"]
    assert juan["risk_level"] == "alto"                 # jornada 48h -> g1
    assert any(g["gap_id"] == "g1" for g in juan["gaps"])
    assert juan["total_exposure"] > 0                   # M4 calculó (salario leído de Money)
    maria = by_name["MARIA GOMEZ"]["summary"]
    assert maria["risk_level"] == "bajo"                # 42h, indefinido reciente -> sin gaps
    assert maria["gaps"] == []


def test_result_completo_tiene_los_4_modulos():
    r = client.post("/api/batch/ingest", headers=AUTH,
                    files={"files": ("lote.zip", _zip(_C_48H), "application/zip")})
    bid = r.json()["batch_id"]
    st = _wait_done(bid)
    doc_id = st["results"][0]["doc_id"]
    res = client.get(f"/api/batch/result/{bid}/{doc_id}", headers=AUTH).json()
    assert set(res) >= {"extract", "compliance", "liquidation", "remediation"}
    assert res["liquidation"]["items"]["total"] > 0
    assert res["remediation"] is not None               # tiene gap -> genera subsanación


def test_archivos_sueltos_tambien_funcionan():
    r = client.post("/api/batch/ingest", headers=AUTH, files=[
        ("files", ("a.txt", _C_48H, "text/plain")),
        ("files", ("b.txt", _C_LIMPIO, "text/plain")),
    ])
    assert r.json()["total"] == 2


def test_carga_sin_contratos_validos_da_400():
    r = client.post("/api/batch/ingest", headers=AUTH,
                    files={"files": ("notas.bin", b"\x00\x01", "application/octet-stream")})
    assert r.status_code == 400


def test_aislamiento_por_tenant():
    r = client.post("/api/batch/ingest", headers=AUTH,
                    files={"files": ("lote.zip", _zip(_C_48H), "application/zip")})
    bid = r.json()["batch_id"]
    _wait_done(bid)
    # Tenant B no puede ver el batch de A.
    assert client.get(f"/api/batch/status/{bid}", headers=AUTH_B).status_code == 404


def test_requiere_api_key():
    r = client.post("/api/batch/ingest",
                    files={"files": ("lote.zip", _zip(_C_48H), "application/zip")})
    assert r.status_code == 401


def test_batch_alimenta_el_dashboard_de_inicio():
    # Tras subir un lote, el dashboard refleja la exposición REAL (no el demo $71M).
    r = client.post("/api/batch/ingest", headers=AUTH,
                    files={"files": ("lote.zip", _zip(_C_48H, _C_LIMPIO), "application/zip")})
    _wait_done(r.json()["batch_id"])
    d = client.get("/api/dashboard/exposure?company_id=empresa-001", headers=AUTH).json()
    # 1 trabajador en riesgo (el de 48h) — NO el 71.175.000 del demo.
    assert d["magic_number"]["cop_exposure"] != 71_175_000.0
    assert d["magic_number"]["outdated_clauses"] >= 1


def test_latest_permite_revisitar_el_ultimo_lote():
    r = client.post("/api/batch/ingest", headers=AUTH,
                    files={"files": ("lote.zip", _zip(_C_48H, _C_LIMPIO), "application/zip")})
    bid = r.json()["batch_id"]
    _wait_done(bid)
    lat = client.get("/api/batch/latest", headers=AUTH).json()
    assert lat["batch_id"] == bid
    assert len([x for x in lat["results"] if x.get("summary")]) == 2


def test_latest_vacio_si_no_hay_lotes():
    # Tenant B nunca subió nada → latest vacío (no rompe).
    lat = client.get("/api/batch/latest", headers=AUTH_B).json()
    assert lat["batch_id"] is None and lat["results"] == []
