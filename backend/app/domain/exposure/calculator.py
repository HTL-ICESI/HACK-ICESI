"""
M6 — Calculadora de exposición (el NÚMERO MÁGICO). NÚCLEO DETERMINISTA.

Convierte gaps normativos + infracciones en COP de exposición a sanción.
Función pura: mismo set -> mismo COP, reproducible y auditable en sala.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.liquidation.constants import smlmv


@dataclass(frozen=True)
class ExposureInput:
    workers_at_risk: int
    detected_reliquidations: float   # COP, suma de diferencias de liquidación
    total_clauses: int               # para el % de desactualización
    outdated_clauses: int
    year: int = 2026


@dataclass(frozen=True)
class MagicNumber:
    outdated_clauses: int
    pct_outdated: float
    cop_exposure: float
    formula: str


def compute(inp: ExposureInput) -> MagicNumber:
    """Exposición = trabajadores_en_riesgo * SMLMV (mora art. 65 CST) + reliquidaciones.

    Con datos REALES del lote, `workers_at_risk=0` y la exposición es la económica de
    las liquidaciones (M4) — el mismo total que Compliance. El proxy de sanciones
    (× SMLMV) solo aplica cuando no hay liquidaciones calculadas (p.ej. el demo)."""
    base = inp.workers_at_risk * smlmv(inp.year)
    exposure = base + inp.detected_reliquidations
    pct = (inp.outdated_clauses / inp.total_clauses * 100) if inp.total_clauses else 0.0
    formula = (f"{inp.workers_at_risk} * SMLMV({inp.year}) + reliquidaciones"
               if inp.workers_at_risk
               else "exposición económica del lote (liquidaciones M4)")
    return MagicNumber(
        outdated_clauses=inp.outdated_clauses,
        pct_outdated=round(pct, 1),
        cop_exposure=exposure,
        formula=formula,
    )
