"""
E2E del ORQUESTADOR: sube un ZIP de varios contratos de una empresa y verifica que
el dashboard (número mágico) sale DERIVADO de los contratos reales, no del demo fijo.

Prueba la integración completa: ZIP → M1 → M2 (LLM real) → M3 → agregación → M6.
Uso: PYTHONPATH=. .venv/bin/python scripts/e2e_company.py
"""
from __future__ import annotations

import io
import zipfile

import fitz
from fastapi.testclient import TestClient

from app.main import app

H = {"Authorization": "Bearer demo-hg-key"}

CONTRATOS = {
    "01_ospino_indefinido.pdf": (
        "CONTRATO INDIVIDUAL DE TRABAJO A TERMINO INDEFINIDO\n"
        "Empleador: EMPRESA CLIENTE SAS, NIT 900.123.456-7\n"
        "Trabajador: JOSE ANDRES OSPINO BURGOS, C.C. 1.042.440.655\n"
        "Cargo: AGENTE DE VENTAS DE CALL CENTER\n"
        "Salario: salario basico mensual de UN MILLON SETECIENTOS CINCUENTA MIL "
        "NOVECIENTOS CINCO PESOS (1.750.905) mas comisiones.\n"
        "Auxilio de transporte: 249.095\n"
        "Jornada: cuarenta y ocho (48) horas semanales.\n"
        "Fecha de inicio: 14 de enero de 2025.\n"),
    "02_ana_prestacion.pdf": (
        "CONTRATO DE PRESTACION DE SERVICIOS PROFESIONALES\n"
        "Contratante: TECHVALLE SOLUTIONS SAS, NIT 900.765.432-1\n"
        "Contratista: ANA SOFIA RESTREPO CARDONA, C.C. 1.144.056.789\n"
        "Cargo: DESARROLLADORA DE SOFTWARE SENIOR\n"
        "Honorarios: honorarios mensuales de CUATRO MILLONES DE PESOS (4.000.000).\n"
        "Jornada: cuarenta y ocho (48) horas semanales.\n"
        "Fecha de inicio: 1 de septiembre de 2025.\n"),
    "03_pedro_fijo_vencido.pdf": (
        "CONTRATO INDIVIDUAL DE TRABAJO A TERMINO FIJO\n"
        "Empleador: LOGISTICA DEL VALLE SAS, NIT 901.222.333-4\n"
        "Trabajador: PEDRO PEREZ GOMEZ, C.C. 16.789.012\n"
        "Cargo: OPERARIO DE BODEGA\n"
        "Salario: salario basico mensual de UN MILLON QUINIENTOS MIL PESOS (1.500.000).\n"
        "Jornada: cuarenta y ocho (48) horas semanales.\n"
        "Fecha de inicio: 1 de marzo de 2024. Fecha de terminacion: 28 de febrero de 2025.\n"),
}


def _pdf(text: str) -> bytes:
    d = fitz.open(); p = d.new_page(); p.insert_text((50, 60), text, fontsize=11)
    b = d.tobytes(); d.close(); return b


def _zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, text in CONTRATOS.items():
            z.writestr(name, _pdf(text))
        # Nómina poblada (marco CO): cruza por cédula → M4 liquida → reliquidaciones.
        with open("data/nomina_demo.csv", "rb") as f:
            z.writestr("nomina_demo.csv", f.read())
    return buf.getvalue()


def main() -> None:
    c = TestClient(app)

    print("=" * 72 + "\nPASO 1 — Dashboard ANTES de analizar (debería ser demo o cero)\n" + "=" * 72)
    r0 = c.get("/api/dashboard/exposure?company_id=empresa-001", headers=H).json()
    print("  cop_exposure (antes):", f"{r0['magic_number']['cop_exposure']:,.0f}")

    print("\n" + "=" * 72 + "\nPASO 2 — POST /api/company/analyze con un ZIP de 3 contratos\n" + "=" * 72)
    r = c.post("/api/company/analyze", headers=H,
               files={"files": ("empresa.zip", _zip(), "application/zip")})
    assert r.status_code == 200, r.text
    body = r.json()
    print("  procesados:", body["procesados"])
    for d in body["documents"]:
        print(f"   - {d['filename']:30} {d.get('vinculo','-'):22} gaps={d.get('gaps',[])}")

    mn = body["dashboard"]["magic_number"]
    print("\n  NÚMERO MÁGICO (derivado de los 3 contratos REALES):")
    print(f"    trabajadores en riesgo : {mn['outdated_clauses']} gaps en total")
    print(f"    % desactualización     : {mn['pct_outdated']}%")
    print(f"    cop_exposure           : ${mn['cop_exposure']:,.0f}")
    print(f"    fórmula                : {mn['exposure_formula']}")
    print(f"    alertas                : {len(body['dashboard']['alerts'])}")

    print("\n" + "=" * 72 + "\nPASO 3 — GET dashboard DESPUÉS (debe leer lo REAL, no el 71M)\n" + "=" * 72)
    r2 = c.get("/api/dashboard/exposure?company_id=empresa-001", headers=H).json()
    cop = r2["magic_number"]["cop_exposure"]
    print(f"  cop_exposure (después): ${cop:,.0f}")
    assert cop != 71_175_000.0, "❌ el dashboard sigue sirviendo el demo hardcodeado"
    assert cop == mn["cop_exposure"], "❌ el dashboard no coincide con el análisis"
    print("  ✅ el dashboard refleja los contratos analizados, NO el demo fijo")


if __name__ == "__main__":
    main()
