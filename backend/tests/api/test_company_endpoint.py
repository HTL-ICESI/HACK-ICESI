"""
Tests del orquestador (POST /api/company/analyze) y su conexión con el dashboard.
Offline (sin LLM): los campos blandos quedan not_found, pero los gaps de campos DUROS
(jornada 48h → g1, vencimiento → g4) sí disparan, así que el número mágico se deriva real.
"""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

fitz = pytest.importorskip("fitz")

from app.main import app
from app.domain.liquidation.constants import smlmv

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-hg-key"}

_C1 = ("CONTRATO INDIVIDUAL DE TRABAJO A TERMINO INDEFINIDO\n"
       "Trabajador: JUAN PEREZ, C.C. 79.000.111\n"
       "Salario: salario basico mensual de DOS MILLONES DE PESOS (2.000.000).\n"
       "Jornada: cuarenta y ocho (48) horas semanales.\n"
       "Fecha de inicio: 1 de enero de 2025.\n")
_C2 = ("CONTRATO INDIVIDUAL DE TRABAJO A TERMINO FIJO\n"
       "Trabajador: LUISA GOMEZ, C.C. 1.130.000.222\n"
       "Salario: salario basico mensual de UN MILLON QUINIENTOS MIL PESOS (1.500.000).\n"
       "Jornada: cuarenta y ocho (48) horas semanales.\n"
       "Fecha de inicio: 1 de marzo de 2024. Fecha de terminacion: 28 de febrero de 2025.\n")


def _pdf(text: str) -> bytes:
    d = fitz.open(); p = d.new_page(); p.insert_text((50, 60), text, fontsize=11)
    b = d.tobytes(); d.close(); return b


def _zip(*texts: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for i, t in enumerate(texts):
            z.writestr(f"contrato_{i+1}.pdf", _pdf(t))
    return buf.getvalue()


def test_analyze_zip_procesa_todos_los_contratos():
    r = client.post("/api/company/analyze", headers=AUTH,
                    files={"files": ("e.zip", _zip(_C1, _C2), "application/zip")})
    assert r.status_code == 200
    body = r.json()
    assert body["procesados"]["contratos"] == 2
    # Ambos tienen jornada 48h → al menos g1 cada uno.
    assert all("g1" in d["gaps"] for d in body["documents"])


def test_numero_magico_se_deriva_no_es_hardcodeado():
    r = client.post("/api/company/analyze", headers=AUTH,
                    files={"files": ("e.zip", _zip(_C1, _C2), "application/zip")})
    mn = r.json()["dashboard"]["magic_number"]
    # 2 trabajadores en riesgo * SMLMV 2026, NO el 71.175.000 del demo.
    assert mn["cop_exposure"] == pytest.approx(2 * smlmv(2026), abs=1)
    assert mn["cop_exposure"] != 71_175_000.0


def test_dashboard_lee_lo_analizado_no_el_demo():
    # Tras analizar, el dashboard del tenant refleja lo real (no _demo_request).
    a = client.post("/api/company/analyze", headers=AUTH,
                    files={"files": ("e.zip", _zip(_C1), "application/zip")}).json()
    cop_analisis = a["dashboard"]["magic_number"]["cop_exposure"]
    d = client.get("/api/dashboard/exposure?company_id=empresa-001", headers=AUTH).json()
    assert d["magic_number"]["cop_exposure"] == cop_analisis
    assert d["magic_number"]["cop_exposure"] != 71_175_000.0


def test_archivo_no_soportado_se_reporta_no_rompe():
    r = client.post("/api/company/analyze", headers=AUTH,
                    files={"files": ("notas.bin", b"\x00\x01basura", "application/octet-stream")})
    assert r.status_code == 200
    assert r.json()["documents"][0]["status"] == "formato_no_soportado"


def test_analyze_requiere_api_key():
    r = client.post("/api/company/analyze",
                    files={"files": ("e.zip", _zip(_C1), "application/zip")})
    assert r.status_code == 401


# Nómina poblada que cruza con _C1 (C.C. 79.000.111) — la cédula la extrae el regex,
# así que el cruce funciona offline sin LLM.
_NOMINA = (
    "cedula,salario_basico,promedio_variable,auxilio_transporte,"
    "dias_pendientes_vacaciones,pago_ss_mora,ss_monto_mora,ss_due_date\n"
    "79000111,2000000,500000,0,12,true,180000,2026-06-25\n"
)


def test_nomina_cruza_por_cedula_y_suma_reliquidaciones():
    r = client.post("/api/company/analyze", headers=AUTH, files=[
        ("files", ("c.pdf", _pdf(_C1), "application/pdf")),
        ("files", ("nomina.csv", _NOMINA.encode(), "text/csv")),
    ])
    assert r.status_code == 200
    body = r.json()
    assert body["procesados"]["nominas"] == 1
    # M4 liquidó al trabajador cruzado por cédula → prestaciones pendientes > 0.
    doc = next(d for d in body["documents"] if d["tipo"] == "contrato")
    assert doc["prestaciones_pendientes"] and doc["prestaciones_pendientes"] > 0
    # El número mágico incluye reliquidaciones (supera 1 trabajador × SMLMV).
    assert body["dashboard"]["magic_number"]["cop_exposure"] > smlmv(2026)
    # La mora SS de la nómina produce alerta real.
    tipos = {a["type"] for a in body["dashboard"]["alerts"]}
    assert "seguridad_social_mora" in tipos


def test_sin_nomina_no_hay_reliquidaciones():
    # Sin nómina, el contrato no tiene prestaciones pendientes (solo gaps).
    r = client.post("/api/company/analyze", headers=AUTH,
                    files={"files": ("c.pdf", _pdf(_C1), "application/pdf")})
    doc = r.json()["documents"][0]
    assert doc["prestaciones_pendientes"] is None


# ── Persistencia en BD + aislamiento multitenant ─────────────────────────────
AUTH_B = {"Authorization": "Bearer demo-key-2"}  # tenant empresa-002


def test_persistencia_en_bd_contratos_y_gaps():
    client.post("/api/company/analyze", headers=AUTH,
                files={"files": ("e.zip", _zip(_C1, _C2), "application/zip")})
    h = client.get("/api/company/history", headers=AUTH).json()
    assert h["total_contratos"] == 2
    assert h["total_gaps"] >= 2          # al menos g1 por contrato
    # Los gaps quedan ligados a su contrato en la BD.
    assert all("g1" in c["gaps"] for c in h["contratos"])


def test_aislamiento_multitenant_en_bd():
    # Tenant A analiza 2 contratos.
    client.post("/api/company/analyze", headers=AUTH,
                files={"files": ("e.zip", _zip(_C1, _C2), "application/zip")})
    # Tenant B NO ve nada de A en la BD (scoping por tenant_id).
    hb = client.get("/api/company/history", headers=AUTH_B).json()
    assert hb["total_contratos"] == 0
    assert hb["total_gaps"] == 0


def test_reanalisis_reemplaza_no_duplica():
    z = _zip(_C1, _C2)
    client.post("/api/company/analyze", headers=AUTH, files={"files": ("e.zip", z, "application/zip")})
    n1 = client.get("/api/company/history", headers=AUTH).json()["total_contratos"]
    # Re-analizar el mismo lote NO debe duplicar las filas en la BD.
    client.post("/api/company/analyze", headers=AUTH, files={"files": ("e.zip", z, "application/zip")})
    n2 = client.get("/api/company/history", headers=AUTH).json()["total_contratos"]
    assert n1 == n2 == 2


def test_vinculo_type_es_determinista_sin_llm():
    # Offline (sin LLM), el tipo de contrato igual se extrae del título por regex,
    # así que g4 (vencido) dispara aunque el LLM esté apagado.
    fijo_vencido = ("CONTRATO INDIVIDUAL DE TRABAJO A TERMINO FIJO\n"
                    "Trabajador: PEPE, C.C. 8.111.222\n"
                    "Jornada: cuarenta y dos (42) horas semanales.\n"
                    "Fecha de inicio: 1 de enero de 2024. Fecha de terminacion: 31 de diciembre de 2024.\n")
    r = client.post("/api/company/analyze", headers=AUTH,
                    files={"files": ("c.pdf", _pdf(fijo_vencido), "application/pdf")})
    doc = r.json()["documents"][0]
    assert doc["vinculo"] == "termino_fijo"   # determinista, sin LLM
    assert "g4" in doc["gaps"]                 # vencido → g4 dispara
