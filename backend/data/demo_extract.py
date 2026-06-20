"""
Demo end-to-end del pipeline M2 (Extractor con cita).

Corre sin servidor: usa el service directamente via asyncio.
Sin ANTHROPIC_API_KEY los campos blandos degradan honestamente a 'not_found'
(eso es correcto: no inventamos). Con API key el LLM completaria role, employer
y vinculo_type con su span verificado.

Uso:
    cd cerebro-laboral-hg/backend
    source .venv/bin/activate
    python data/demo_extract.py
"""
import asyncio
import json
import textwrap
from pathlib import Path

# Asegura imports desde la raiz del backend.
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.adapters.storage.repository import InMemoryRepository
from app.adapters.llm.claude_client import ClaudeClient
from app.domain.models import FieldStatus
from app.services.extraction_service import ExtractionService

CONTRATO_PATH = Path(__file__).parent / "contrato_hg_ejemplo.txt"

STATUS_ICON = {
    FieldStatus.OK:          "✅",
    FieldStatus.NEEDS_HUMAN: "🟡",
    FieldStatus.NOT_FOUND:   "⬜",
}

SEP = "─" * 72


def fmt_field(name: str, field) -> str:
    icon = STATUS_ICON[field.status]
    val = field.value
    if val is None:
        val_str = "(no encontrado)"
    elif hasattr(val, "model_dump"):
        val_str = json.dumps(val.model_dump(), ensure_ascii=False)
    else:
        val_str = str(val)

    src_str = ""
    if field.source:
        src_str = (
            f"\n    📌 span [{field.source.span_start}:{field.source.span_end}]"
            f"  conf={field.source.confidence:.2f}"
            f"\n    \"{field.source.text}\""
        )
    return f"  {icon} {name:<18} {val_str}{src_str}"


async def main() -> None:
    text = CONTRATO_PATH.read_text(encoding="utf-8")

    print(SEP)
    print("  CEREBRO LABORAL HG — Pipeline M2: Extractor con cita")
    print(SEP)
    print(f"  Documento : {CONTRATO_PATH.name}")
    print(f"  Caracteres: {len(text)}")
    print()
    print("  [Extractores deterministas: regex puro, sin LLM]")
    print("  [Campos blandos: LLM con span verificado; sin API key → 'not_found' honesto]")
    print(SEP)

    ctx = TenantContext(tenant_id="empresa-hg-demo")
    svc = ExtractionService(InMemoryRepository(), AuditLog(), ClaudeClient())
    rec = await svc.extract(ctx, "contrato-demo-001", text)

    print()
    print("  CAMPOS EXTRAIDOS:")
    print()

    fields = [
        ("vinculo_type",  rec.vinculo_type),
        ("base_salary",   rec.base_salary),
        ("start_date",    rec.start_date),
        ("end_date",      rec.end_date),
        ("weekly_hours",  rec.weekly_hours),
        ("role",          rec.role),
        ("employer",      rec.employer),
    ]
    for name, field in fields:
        print(fmt_field(name, field))
        print()

    # Resumen estadistico.
    ok     = sum(1 for _, f in fields if f.status == FieldStatus.OK)
    human  = sum(1 for _, f in fields if f.status == FieldStatus.NEEDS_HUMAN)
    nf     = sum(1 for _, f in fields if f.status == FieldStatus.NOT_FOUND)

    print(SEP)
    print(f"  Resumen: ✅ {ok} ok  |  🟡 {human} needs_human  |  ⬜ {nf} not_found")

    numeric_with_source = all(
        f.source is not None
        for name, f in fields
        if name in ("base_salary", "start_date", "end_date", "weekly_hours")
        and f.status == FieldStatus.OK
    )
    print()
    if numeric_with_source:
        print("  GARANTIA ANTI-ALUCINACION: todos los numeros tienen source (span citado). ✅")
    else:
        print("  ALERTA: algun campo numerico esta OK pero sin source. Revisar. ❌")
    print(SEP)


if __name__ == "__main__":
    asyncio.run(main())
