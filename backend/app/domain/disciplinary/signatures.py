"""Modelo de firmas del acta de descargos."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.disciplinary.attendees import Attendee


@dataclass
class ActaSignatures:
    instructor_signed: bool
    worker_signed: bool
    worker_refusal: bool
    witnesses: list[Attendee] = field(default_factory=list)
    signed_at: datetime | None = None

    def is_valid(self) -> bool:
        if self.worker_signed:
            return self.instructor_signed
        if self.worker_refusal:
            return self.instructor_signed and len(self.witnesses) >= 2
        return False

    def to_dict(self) -> dict:
        return {
            "instructor_signed": self.instructor_signed,
            "worker_signed": self.worker_signed,
            "worker_refusal": self.worker_refusal,
            "witnesses": [w.to_dict() for w in self.witnesses],
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
            "is_valid": self.is_valid(),
        }
