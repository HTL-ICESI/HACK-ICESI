"""
Prueba E2E — CASO 2: falso independiente (prestación de servicios).

Distinto al caso gold (Ospino, indefinido → g1+g3): este ejercita la rama
ESTRELLA para el jurado → g2 reclasificación (Ley 2466/2025) + g1 jornada.

Genera su propio PDF, corre M1 → M2 → M3 reales (solo los 3 campos blandos del
LLM se stubean, igual que e2e_gold.py) y verifica los gaps esperados.

Uso: PYTHONPATH=. .venv/bin/python scripts/e2e_caso_prestacion.py
"""
from __future__ import annotations

import asyncio

import fitz  # PyMuPDF

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.adapters.storage.repository import InMemoryRepository
from app.services.ingest_service import IngestService
from app.services.extraction_service import ExtractionService
from app.services.compliance_service import ComplianceService

PDF = "/tmp/contrato_prestacion_ana.pdf"
CTX = TenantContext(tenant_id="hurtado-gandini", actor="e2e-caso2")

CONTRATO = (
    "CONTRATO DE PRESTACION DE SERVICIOS PROFESIONALES\n"
    "Contratante: TECHVALLE SOLUTIONS SAS, NIT 900.765.432-1\n"
    "Contratista: ANA SOFIA RESTREPO CARDONA, C.C. 1.144.056.789\n"
    "Cargo: DESARROLLADORA DE SOFTWARE SENIOR\n"
    "Centro de costos: Cali\n"
    "Honorarios: honorarios mensuales de CUATRO MILLONES DE PESOS (4.000.000).\n"
    "Jornada: cuarenta y ocho (48) horas semanales, de lunes a viernes en las\n"
    "instalaciones del contratante.\n"
    "Exclusividad: la contratista no podra prestar servicios a terceros.\n"
    "Herramientas: el contratante suministra equipo de computo y licencias.\n"
    "Fecha de inicio: 1 de septiembre de 2025.\n"
)


class StubLLM:
    """Solo los 3 campos blandos del caso 2; el service localiza los spans real."""
    async def extract_soft_fields(self, text: str, schema: dict) -> dict:
        return {
            "vinculo_type": {"value": "prestacion_servicios",
                             "span_start": 0, "span_end": 0, "confidence": 0.96},
            "role":         {"value": "DESARROLLADORA DE SOFTWARE SENIOR",
                             "span_start": 0, "span_end": 0, "confidence": 0.95},
            "employer":     {"value": {"name": "TECHVALLE SOLUTIONS SAS", "nit": "900.765.432-1"},
                             "span_start": 0, "span_end": 0, "confidence": 0.92},
        }


def _make_pdf() -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 60), CONTRATO, fontsize=11)
    doc.save(PDF)
    doc.close()


def _f(field) -> str:
    if field is None:
        return "None"
    src = field.source
    cita = f' ⟵ "{src.text[:45]}" (conf {src.confidence})' if src else " (sin source)"
    return f"{field.value!r} [{field.status.value}]{cita}"


async def main() -> None:
    _make_pdf()
    audit, repo = AuditLog(), InMemoryRepository()

    print("\n" + "=" * 72 + "\nM1 — INGESTA (real)\n" + "=" * 72)
    res = IngestService(repo, audit).ingest_document(
        CTX, "caso2-ana", open(PDF, "rb").read(), "contrato_prestacion_ana.pdf")
    print(f"status={res.status}  confianza={res.confidence}  chars={len(res.text)}")

    from app.config import get_settings
    if get_settings().infermatic_api_key or get_settings().anthropic_api_key:
        from app.adapters.llm.claude_client import ClaudeClient
        llm, modo = ClaudeClient(), "TotalGPT/LLM REAL"
    else:
        llm, modo = StubLLM(), "stub (sin API key)"
    print("\n" + "=" * 72 + f"\nM2 — EXTRACTOR (duros=regex · blandos={modo})\n" + "=" * 72)
    record = await ExtractionService(repo, audit, llm).extract(CTX, "caso2-ana", res.text)
    for nombre in ("vinculo_type", "empleado_nombre", "empleado_documento", "role",
                   "employer", "base_salary", "salario_variable", "start_date",
                   "end_date", "weekly_hours", "termination_confirmed"):
        print(f"  {nombre:22} = {_f(getattr(record, nombre))}")

    print("\n" + "=" * 72 + "\nM3 — COMPLIANCE (reglas reales)\n" + "=" * 72)
    result = ComplianceService(audit).analyze(CTX, "caso2-ana", record, "contrato")
    print(f"gaps: {len(result['gaps'])}  |  risk_score: {result['summary']['risk_score']}  |  "
          f"blocking: {result['summary']['has_blocking_issues']}")
    for g in result["gaps"]:
        cit = g.get("citation") or {}
        print(f"\n  ▸ {g['gap_id']} [{g['severity'].upper()}] {cit.get('norm_id','?')} {cit.get('article','')}")
        print(f"    {g['issue']}")

    print("\n" + "=" * 72 + "\nVERIFICACIÓN vs CASO 2 (falso independiente)\n" + "=" * 72)
    gap_ids = {g["gap_id"] for g in result["gaps"]}
    checks = [
        ("M1 leyó el PDF (digital)", res.status == "digital"),
        ("M2 nombre = ANA SOFIA RESTREPO CARDONA",
         "RESTREPO" in str(record.empleado_nombre.value or "").upper()),
        ("M2 vinculo = prestacion_servicios", record.vinculo_type.value == "prestacion_servicios"),
        ("M2 jornada = 48", record.weekly_hours.value == 48),
        ("M2 inicio = 2025-09-01", str(record.start_date.value) == "2025-09-01"),
        ("M2 honorarios NO se extraen como salario (honesto)",
         record.base_salary.status.value == "not_found"),
        ("M3 detecta g2 (reclasificación Ley 2466) ⭐", "g2" in gap_ids),
        ("M3 detecta g1 (jornada 48h > 42h)", "g1" in gap_ids),
        ("M3 NO detecta g3 (<1 año, sin vacaciones acumuladas)", "g3" not in gap_ids),
        ("M3 NO detecta g4 (no es término fijo)", "g4" not in gap_ids),
        ("M3 NO detecta g5 (sin mora comprobada)", "g5" not in gap_ids),
    ]
    ok = sum(1 for _, c in checks if c)
    for label, cond in checks:
        print(f"  {'✅' if cond else '❌'} {label}")
    print(f"\n  {ok}/{len(checks)} verificaciones OK")


if __name__ == "__main__":
    asyncio.run(main())
