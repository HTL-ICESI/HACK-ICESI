"""
Procesa el handoff de M1 con el pipeline real de M2 y produce el input para M3.

Uso:
    cd cerebro-laboral-hg/backend
    source .venv/bin/activate
    python data/process_m1_handoff.py
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.adapters.storage.repository import InMemoryRepository
from app.adapters.llm.claude_client import ClaudeClient
from app.domain.models import FieldStatus
from app.services.extraction_service import ExtractionService

HANDOFF_IN  = Path("/tmp/handoff-m1.json")
HANDOFF_OUT = Path("/tmp/handoff-m2.json")

SEP = "─" * 72
STATUS_ICON = {
    FieldStatus.OK:          "✅ ok",
    FieldStatus.NEEDS_HUMAN: "🟡 needs_human",
    FieldStatus.NOT_FOUND:   "⬜ not_found",
}


def _field_summary(name: str, field) -> str:
    icon = STATUS_ICON[field.status]
    val = field.value
    if val is None:
        val_str = "—"
    elif hasattr(val, "model_dump"):
        d = val.model_dump()
        val_str = json.dumps(d, ensure_ascii=False)
    else:
        val_str = str(val)

    src = ""
    if field.source:
        src = (f"  →  span [{field.source.span_start}:{field.source.span_end}]"
               f"  \"{field.source.text}\"  conf={field.source.confidence:.2f}")
    return f"  {icon:<20}  {name:<18}  {val_str}{src}"


async def main() -> None:
    # 1. Leer handoff M1
    payload = json.loads(HANDOFF_IN.read_text())
    doc_id  = payload["_input_para_M2"]["doc_id"]
    text    = payload["_input_para_M2"]["text"]
    tenant  = payload.get("_tenant", "empresa-001")

    print(SEP)
    print("  PIPELINE M1 → M2 → [M3]")
    print(SEP)
    print(f"  Handoff M1 : {HANDOFF_IN}")
    print(f"  doc_id     : {doc_id}")
    print(f"  tenant     : {tenant}")
    print(f"  confidence : {payload.get('confidence', '?')}")
    print(f"  status M1  : {payload.get('status', '?')}")
    print()
    print("  TEXTO INGERIDO (M1 output):")
    for line in text.splitlines():
        print(f"    {line}")
    print()
    print(SEP)

    # 2. Correr M2 con el service real
    ctx = TenantContext(tenant_id=tenant)
    svc = ExtractionService(InMemoryRepository(), AuditLog(), ClaudeClient())
    record = await svc.extract(ctx, doc_id, text)

    # 3. Mostrar resultado campo por campo
    print()
    print("  RESULTADO M2 — DocumentRecord extraído:")
    print()
    fields = [
        ("vinculo_type",          record.vinculo_type),
        ("base_salary",           record.base_salary),
        ("start_date",            record.start_date),
        ("end_date",              record.end_date),
        ("weekly_hours",          record.weekly_hours),
        ("role",                  record.role),
        ("employer",              record.employer),
        ("termination_confirmed", record.termination_confirmed),
    ]
    for name, field in fields:
        print(_field_summary(name, field))

    ok    = sum(1 for _, f in fields if f.status == FieldStatus.OK)
    human = sum(1 for _, f in fields if f.status == FieldStatus.NEEDS_HUMAN)
    nf    = sum(1 for _, f in fields if f.status == FieldStatus.NOT_FOUND)

    numeric_ok = all(
        f.source is not None
        for name, f in fields
        if name in ("base_salary", "start_date", "end_date", "weekly_hours")
        and f.status == FieldStatus.OK
    )

    print()
    print(SEP)
    print(f"  Resumen: ✅ {ok} ok  |  🟡 {human} needs_human  |  ⬜ {nf} not_found")
    guarantee = "✅ GARANTIA CUMPLIDA" if numeric_ok else "❌ ALERTA: numero sin source"
    print(f"  Anti-alucinación numérica: {guarantee}")
    print(SEP)

    # 4. Serializar record para M3
    def _field_json(f):
        val = f.value
        if val is None:
            val_out = None
        elif hasattr(val, "model_dump"):
            val_out = val.model_dump()
        else:
            val_out = val

        src_out = None
        if f.source:
            src_out = {
                "span_start": f.source.span_start,
                "span_end":   f.source.span_end,
                "text":       f.source.text,
                "confidence": f.source.confidence,
                "doc_id":     f.source.doc_id,
            }
        return {"value": val_out, "source": src_out, "status": f.status.value}

    record_json = {name: _field_json(field) for name, field in fields}

    handoff_m3 = {
        "_pipeline":       "M2 extractor (listo para M3)",
        "_tenant":         tenant,
        "_m1_confidence":  payload.get("confidence"),
        "_m1_status":      payload.get("status"),
        "doc_id":          doc_id,
        "record":          record_json,
        "_input_para_M3": {
            "doc_id":   doc_id,
            "record":   record_json,
            "doc_type": "contrato",
        },
    }

    HANDOFF_OUT.write_text(json.dumps(handoff_m3, ensure_ascii=False, indent=2))
    print()
    print(f"  Handoff M3 guardado → {HANDOFF_OUT}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
