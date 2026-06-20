"""Modelo de asistentes a la diligencia de descargos."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AttendeeRole = Literal[
    "instructor",
    "trabajador",
    "delegado_sindical",
    "companero_trabajo",
    "testigo",
    "abogado_empleado",
    "otro",
]


@dataclass
class Attendee:
    name: str
    role: AttendeeRole
    identification: str | None = None

    def to_dict(self) -> dict:
        return {"name": self.name, "role": self.role, "identification": self.identification}
