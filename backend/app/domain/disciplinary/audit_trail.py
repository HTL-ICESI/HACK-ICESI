"""Audit trail inmutable del proceso disciplinario J1.

Solo INSERT — nunca UPDATE ni DELETE. Cada cambio de estado genera una entrada.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PipelineAuditEntry:
    entry_id: str
    process_id: str
    timestamp: datetime
    actor: str
    from_state: str | None
    to_state: str
    reason: str | None
    payload_summary: str

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "process_id": self.process_id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "reason": self.reason,
            "payload_summary": self.payload_summary,
        }
