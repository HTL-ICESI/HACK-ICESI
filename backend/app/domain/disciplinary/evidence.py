"""Modelo de evidencias del expediente disciplinario."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class Evidence:
    evidence_id: str
    filename: str
    file_type: Literal["pdf", "image", "eml"]
    sha256: str
    uploaded_at: datetime
    uploaded_by: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "sha256": self.sha256,
            "uploaded_at": self.uploaded_at.isoformat(),
            "uploaded_by": self.uploaded_by,
            "metadata": self.metadata,
        }
