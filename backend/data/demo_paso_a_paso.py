"""
Demo paso a paso del pipeline M2.
Muestra cada capa: LLM crudo -> validacion del service -> output para M3.
"""
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.adapters.storage.repository import InMemoryRepository
from app.adapters.llm.claude_client import ClaudeClient
from app.domain.models import FieldStatus
from app.services.extraction_service import ExtractionService, SOFT_FIELDS_SCHEMA

S = get_settings()
SEP  = "─" * 68
SEP2 = "═" * 68

CONTRATO = """\
CONTRATO INDIVIDUAL DE TRABAJO A TERMINO FIJO
Empleador: EMPRESA CLIENTE SAS, NIT 900.123.456-7
Trabajador: JUAN PEREZ, C.C. 1.144.000.000
Cargo: Asesor comercial
Salario mensual: 2.500.000 pesos
Jornada: 48 horas semanales
Fecha de inicio: 1 de febrero de 2024
Fecha de terminacion: 31 de enero de 2025"""


async def main():
    llm = ClaudeClient()

    print()
    print(SEP2)
    print("  DEMO M2 — Extractor con cita (paso a paso)")
    print(SEP2)
    print()
    print("  TEXTO DEL CONTRATO (salida de M1):")
    print(SEP)
    for line in CONTRATO.splitlines():
        print(f"  {line}")
    print(SEP)

    # ── PASO 1: LLM crudo ───────────────────────────────────────────────
    print()
    print("  PASO 1 — LLM (Qwen 3.6 via Infermatic)")
    print("           Pregunta: ¿qué campos blandos ves en este contrato?")
    print(SEP)

    backend = "Anthropic" if S.anthropic_api_key else (
              "Infermatic/Qwen" if S.infermatic_api_key else "ninguno (degradacion)")
    print(f"  Backend activo : {backend}")
    print()

    llm_raw = await llm.extract_soft_fields(CONTRATO, SOFT_FIELDS_SCHEMA)
    print("  Respuesta JSON del LLM:")
    print()
    for field, payload in llm_raw.items():
        print(f"    {field}: {json.dumps(payload, ensure_ascii=False)}")
    if not llm_raw:
        print("    (vacio — sin credenciales o texto insuficiente)")

    # ── PASO 2: Validacion del service ──────────────────────────────────
    print()
    print(SEP)
    print("  PASO 2 — Service valida cada campo blando")
    print("           Regla: el valor debe aparecer LITERALMENTE en el texto.")
    print("           Si esta -> span real. Si no -> needs_human.")
    print(SEP)

    from app.services.extraction_service import _locate_value
    for field, payload in llm_raw.items():
        val  = payload.get("value") if isinstance(payload, dict) else payload
        conf = payload.get("confidence") if isinstance(payload, dict) else None
        span = _locate_value(val, CONTRATO)
        if span:
            snippet = CONTRATO[span[0]:span[1]]
            print(f"  {field}")
            print(f"    LLM propone : {json.dumps(val, ensure_ascii=False)}  (conf LLM={conf})")
            print(f"    Service     : encontrado [{span[0]}:{span[1]}] \"{snippet}\"")
            print(f"    Resultado   : ACEPTADO — span determinista, conf={conf}")
        else:
            print(f"  {field}")
            print(f"    LLM propone : {json.dumps(val, ensure_ascii=False)}  (conf LLM={conf})")
            print(f"    Service     : valor NO encontrado en el texto")
            print(f"    Resultado   : NEEDS_HUMAN — no podemos citar la fuente")
        print()

    # ── PASO 3: Campos deterministas (regex) ────────────────────────────
    print(SEP)
    print("  PASO 3 — Regex determinista (salario, fechas, jornada)")
    print("           Sin LLM. Mismo texto -> mismo resultado siempre.")
    print(SEP)

    from app.domain.extraction import (
        extract_salary, extract_start_date, extract_end_date, extract_weekly_hours
    )
    checks = [
        ("base_salary",  extract_salary(CONTRATO)),
        ("start_date",   extract_start_date(CONTRATO)),
        ("end_date",     extract_end_date(CONTRATO)),
        ("weekly_hours", extract_weekly_hours(CONTRATO)),
    ]
    for name, ex in checks:
        if ex:
            print(f"  {name:<14} [{ex.span.start}:{ex.span.end}]  \"{ex.span.text}\"  -> {ex.value}")
        else:
            print(f"  {name:<14} NO ENCONTRADO")

    # ── PASO 4: DocumentRecord final ────────────────────────────────────
    print()
    print(SEP)
    print("  PASO 4 — DocumentRecord completo (output para M3)")
    print(SEP)

    ctx = TenantContext(tenant_id="empresa-001")
    svc = ExtractionService(InMemoryRepository(), AuditLog(), llm)
    rec = await svc.extract(ctx, "contrato-demo", CONTRATO)

    ICONS = {FieldStatus.OK: "✅", FieldStatus.NEEDS_HUMAN: "🟡", FieldStatus.NOT_FOUND: "⬜"}
    fields = [
        ("vinculo_type", rec.vinculo_type),
        ("base_salary",  rec.base_salary),
        ("start_date",   rec.start_date),
        ("end_date",     rec.end_date),
        ("weekly_hours", rec.weekly_hours),
        ("role",         rec.role),
        ("employer",     rec.employer),
    ]
    print()
    for name, f in fields:
        icon = ICONS[f.status]
        val = f.value
        if hasattr(val, "model_dump"):
            val = val.model_dump()
        src = f"span [{f.source.span_start}:{f.source.span_end}] \"{f.source.text}\"" if f.source else "sin source"
        print(f"  {icon} {name:<16} {str(val):<35}  {src}")

    ok = sum(1 for _, f in fields if f.status == FieldStatus.OK)
    nh = sum(1 for _, f in fields if f.status == FieldStatus.NEEDS_HUMAN)
    nf = sum(1 for _, f in fields if f.status == FieldStatus.NOT_FOUND)
    print()
    print(SEP)
    print(f"  Resultado : {ok}/7 ok  |  {nh} needs_human  |  {nf} not_found")
    print(f"  Garantia  : todo numero con span citado verificable")
    print(SEP2)
    print()


if __name__ == "__main__":
    asyncio.run(main())
