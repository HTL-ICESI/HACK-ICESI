"""
Audit trail: registra cada afirmación/acción con su tenant, actor y fuente.

Es parte de la historia anti-alucinación: cada cifra y cada documento queda
trazado a quién lo pidió, sobre qué tenant, y con qué fundamento.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict

from app.core.tenancy import TenantContext


@dataclass
class AuditEntry:
    tenant_id: str
    actor: str
    action: str          # p.ej. "liquidation.compute"
    ref: str             # doc_id / session_id
    grounding: list[str] = field(default_factory=list)  # fuentes/citas
    ts: float = field(default_factory=time.time)


class AuditLog:
    """Append-only. En prod -> tabla/event store; aquí, memoria + stdout."""
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, ctx: TenantContext, action: str, ref: str, grounding: list[str] | None = None) -> None:
        entry = AuditEntry(ctx.tenant_id, ctx.actor, action, ref, grounding or [])
        self._entries.append(entry)
        print("[AUDIT]", json.dumps(asdict(entry), ensure_ascii=False))

    def for_tenant(self, tenant_id: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.tenant_id == tenant_id]
