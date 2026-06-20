"""Configuración de plazos disciplinarios por cliente.

Todos los plazos son ajustables excepto DIAS_HABILES_MINIMOS (límite legal duro).
El validador rechaza min_notice_days < 5 con ValueError.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.disciplinary.norms import DIAS_HABILES_MINIMOS


@dataclass
class DisciplinaryConfig:
    client_id: str
    min_notice_days: int = 5
    max_rounds: int = 2
    days_between_rounds: int = 5
    decision_deadline_days: int = 15
    internal_regulation_ref: str = "RIT"

    def __post_init__(self) -> None:
        if self.min_notice_days < DIAS_HABILES_MINIMOS:
            raise ValueError(
                f"min_notice_days ({self.min_notice_days}) no puede ser menor que "
                f"DIAS_HABILES_MINIMOS ({DIAS_HABILES_MINIMOS}) — límite legal CST art. 115 + Ley 2466/2025."
            )

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id,
            "min_notice_days": self.min_notice_days,
            "max_rounds": self.max_rounds,
            "days_between_rounds": self.days_between_rounds,
            "decision_deadline_days": self.decision_deadline_days,
            "internal_regulation_ref": self.internal_regulation_ref,
        }
