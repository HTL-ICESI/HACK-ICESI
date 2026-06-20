"""
Prueba E2E de la pipeline COMPLETA sobre el caso gold (José Ospino).

Corre M1 → M2 → M3 con los servicios REALES del main integrado:
  - M1 (ingesta/OCR): real, texto del PDF.
  - M2 (extractor): campos DUROS por regex real; solo los 3 campos BLANDOS
    (vinculo_type, role, employer) se sirven con un stub del LLM, porque no hay
    ANTHROPIC_API_KEY en este entorno. El stub solo entrega VALORES; el service
    localiza los spans en el texto por su cuenta (validación anti-alucinación real).
  - M3 (compliance): reglas deterministas reales contra el corpus normativo.

Uso: .venv/bin/python scripts/e2e_gold.py
"""
from __future__ import annotations

import asyncio
import json

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.adapters.storage.repository import InMemoryRepository
from app.services.ingest_service import IngestService
from app.services.extraction_service import ExtractionService
from app.services.compliance_service import ComplianceService
from app.domain.liquidation.engine import liquidate, LiquidationInput

PDF = "/tmp/contrato_jose_ospino.pdf"
CTX = TenantContext(tenant_id="hurtado-gandini", actor="e2e-gold")


class StubLLM:
    """Sustituye SOLO la inferencia del LLM para los 3 campos blandos del gold case.
    Entrega valores; el ExtractionService valida/localiza los spans en el texto real."""
    async def extract_soft_fields(self, text: str, schema: dict) -> dict:
        return {
            "vinculo_type": {"value": "termino_indefinido",
                             "span_start": 0, "span_end": 0, "confidence": 0.97},
            "role":         {"value": "AGENTE DE VENTAS DE CALL CENTER",
                             "span_start": 0, "span_end": 0, "confidence": 0.95},
            "employer":     {"value": {"name": "EMPRESA CLIENTE SAS", "nit": "900.123.456-7"},
                             "span_start": 0, "span_end": 0, "confidence": 0.92},
        }


def _f(field) -> str:
    """Render compacto de un Field con su trazabilidad."""
    if field is None:
        return "None"
    src = field.source
    cita = f' ⟵ "{src.text[:45]}" (conf {src.confidence})' if src else " (sin source)"
    return f"{field.value!r} [{field.status.value}]{cita}"


async def main() -> None:
    audit = AuditLog()
    repo = InMemoryRepository()

    # ── M1: ingesta real ─────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("M1 — INGESTA (real)")
    print("=" * 72)
    ingest = IngestService(repo, audit)
    res = ingest.ingest_document(CTX, "gold-ospino", open(PDF, "rb").read(),
                                 "contrato_jose_ospino.pdf")
    print(f"status={res.status}  confianza={res.confidence}  chars={len(res.text)}")
    assert res.status == "digital", "M1 debería leer el PDF como capa de texto digital"

    # ── M2: extracción (duros reales + blandos: TotalGPT real si hay key) ─────
    from app.config import get_settings
    if get_settings().infermatic_api_key or get_settings().anthropic_api_key:
        from app.adapters.llm.claude_client import ClaudeClient
        llm, modo = ClaudeClient(), "TotalGPT/LLM REAL"
    else:
        llm, modo = StubLLM(), "stub (sin API key)"
    print("\n" + "=" * 72)
    print(f"M2 — EXTRACTOR (duros=regex real · blandos={modo})")
    print("=" * 72)
    extractor = ExtractionService(repo, audit, llm)
    record = await extractor.extract(CTX, "gold-ospino", res.text)

    campos = [
        ("vinculo_type", record.vinculo_type),
        ("empleado_nombre", record.empleado_nombre),
        ("empleado_documento", record.empleado_documento),
        ("role", record.role),
        ("employer", record.employer),
        ("base_salary", record.base_salary),
        ("auxilio_transporte", record.auxilio_transporte),
        ("salario_variable", record.salario_variable),
        ("start_date", record.start_date),
        ("end_date", record.end_date),
        ("weekly_hours", record.weekly_hours),
        ("termination_confirmed", record.termination_confirmed),
    ]
    for nombre, f in campos:
        print(f"  {nombre:22} = {_f(f)}")

    # ── M3: compliance (reglas reales) ───────────────────────────────────────
    print("\n" + "=" * 72)
    print("M3 — COMPLIANCE (reglas deterministas reales)")
    print("=" * 72)
    compliance = ComplianceService(audit)
    result = compliance.analyze(CTX, "gold-ospino", record, "contrato")

    print(f"gaps detectados: {len(result['gaps'])}  |  "
          f"risk_score: {result['summary']['risk_score']}  |  "
          f"blocking: {result['summary']['has_blocking_issues']}")
    for g in result["gaps"]:
        cit = g.get("citation") or {}
        print(f"\n  ▸ {g['gap_id']} [{g['severity'].upper()}] "
              f"{cit.get('norm_id','?')} {cit.get('article','')}")
        print(f"    {g['issue']}")
        if g.get("source"):
            print(f"    cita contrato: \"{g['source']['text'][:55]}\"")

    # ── M4: liquidación (motor determinista) ─────────────────────────────────
    # M2 aporta básico (1.750.905) y auxilio (249.095) DESDE el contrato.
    # El promedio variable (676.785) y los días pendientes (9) son datos
    # operativos de nómina (tabla novedad_nomina), NO del contrato → entran aquí.
    print("\n" + "=" * 72 + "\nM4 — LIQUIDACIÓN (motor determinista, base de M2 + nómina)\n" + "=" * 72)
    liq = liquidate(LiquidationInput(
        salario_basico=_money(record.base_salary),
        auxilio_transporte=_money(record.auxilio_transporte),
        promedio_variable=676_784.614,      # de novedad_nomina (salario variable, valor exacto)
        days_worked=66,                     # 01 ene – 06 mar 2026
        dias_pendientes_vacaciones=9,
        vinculo_type=str(record.vinculo_type.value),
        termination_cause="renuncia",       # acta de renuncia (documento aparte)
    ))
    print(f"  cesantías      = {liq.cesantias:>14,.2f}")
    print(f"  int. cesantías = {liq.intereses_cesantias:>14,.2f}")
    print(f"  prima          = {liq.prima:>14,.2f}")
    print(f"  vacaciones     = {liq.vacaciones:>14,.2f}")
    print(f"  indemnización  = {liq.indemnizacion:>14,.2f}  (renuncia → 0)")
    print(f"  {'─'*32}")
    print(f"  TOTAL PRESTAC. = {liq.total_prestaciones:>14,.2f}  (gold 1.720.590,94)")

    # ── Verificación contra el gold ──────────────────────────────────────────
    print("\n" + "=" * 72)
    print("VERIFICACIÓN vs CASO GOLD")
    print("=" * 72)
    gap_ids = {g["gap_id"] for g in result["gaps"]}
    checks = [
        ("M1 leyó el PDF (digital)", res.status == "digital"),
        ("M2 nombre = JOSE ANDRES OSPINO BURGOS",
         record.empleado_nombre.value and "OSPINO" in str(record.empleado_nombre.value).upper()),
        ("M2 cédula = 1.042.440.655 (normalizada)",
         "".join(c for c in str(record.empleado_documento.value) if c.isdigit()) == "1042440655"),
        ("M2 salario básico = 1.750.905",
         _money(record.base_salary) == 1_750_905),
        ("M2 auxilio transporte = 249.095",
         _money(record.auxilio_transporte) == 249_095),
        ("M2 salario_variable = True", record.salario_variable.value is True),
        ("M2 jornada = 48", record.weekly_hours.value == 48),
        ("M2 inicio = 2025-01-14", str(record.start_date.value) == "2025-01-14"),
        ("M2 indefinido → end_date not_found", record.end_date.status.value == "not_found"),
        ("M3 detecta g1 (jornada 48h > 42h)", "g1" in gap_ids),
        ("M3 NO detecta g2 (no es prestación)", "g2" not in gap_ids),
        ("M3 NO detecta g5 (sin mora comprobada)", "g5" not in gap_ids),
        ("M4 liquidación TOTAL PRESTACIONES = 1.720.590,94 (exacto)",
         abs(liq.total_prestaciones - 1_720_590.94) <= 0.5),
    ]
    ok = 0
    for label, cond in checks:
        mark = "✅" if cond else "❌"
        if cond:
            ok += 1
        print(f"  {mark} {label}")
    print(f"\n  {ok}/{len(checks)} verificaciones OK")


def _money(field) -> float | None:
    v = field.value
    if isinstance(v, dict):
        return v.get("value")
    return getattr(v, "value", v)  # Money pydantic o escalar


if __name__ == "__main__":
    asyncio.run(main())
