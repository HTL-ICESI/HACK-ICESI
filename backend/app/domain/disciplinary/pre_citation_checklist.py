"""Checklist pre-cita — los 4 ítems obligatorios antes de emitir la citación."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PreCitationChecklist:
    worker_id_and_contract: bool = False
    facts_and_date: bool = False
    at_least_one_proof: bool = False
    infringed_norm: bool = False

    @property
    def can_cite(self) -> bool:
        return (
            self.worker_id_and_contract
            and self.facts_and_date
            and self.at_least_one_proof
            and self.infringed_norm
        )

    def missing_items(self) -> list[str]:
        missing = []
        if not self.worker_id_and_contract:
            missing.append("Identificación del trabajador y contrato en el expediente")
        if not self.facts_and_date:
            missing.append("Descripción de los hechos con fecha concreta")
        if not self.at_least_one_proof:
            missing.append("Al menos una prueba cargada y hasheada en el expediente")
        if not self.infringed_norm:
            missing.append("Norma o artículo del RIT invocado")
        return missing

    def to_dict(self) -> dict:
        return {
            "worker_id_and_contract": self.worker_id_and_contract,
            "facts_and_date": self.facts_and_date,
            "at_least_one_proof": self.at_least_one_proof,
            "infringed_norm": self.infringed_norm,
            "can_cite": self.can_cite,
        }
