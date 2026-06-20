"""
M6 Service — orquesta calculator (COP) + alerts (calendario) y devuelve la respuesta del dashboard.

La capa de servicio NO contiene lógica jurídica. Solo coordina dominio + audit.
Reliquidaciones de M4: si M4 no está integrado, passed como 0.0 (el COP se recalcula al llegar).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.core.audit import AuditLog
from app.core.tenancy import TenantContext
from app.domain.exposure.calculator import ExposureInput, compute
from app.domain.exposure.alerts import ContractContext, compute_alerts
from app.domain.liquidation.constants import smlmv

# Número de reglas deterministas que M3 aplica por contrato (g1–g5).
# Si se agrega una regla a gap_rules.py, actualizar este valor.
_NUM_M3_RULES = 5


@dataclass
class ExposureRequest:
    company_id: str
    workers_at_risk: int
    detected_reliquidations: float         # COP; 0.0 hasta que M4 integre
    total_clauses: int
    outdated_clauses: int
    contracts: list[ContractContext] = field(default_factory=list)
    reference_date: date | None = None    # None → date.today() en domain
    year: int = 2026

    @classmethod
    def from_m3_gaps(
        cls,
        company_id: str,
        gap_results: list[dict],           # lista de outputs de ComplianceService.analyze()
        total_clauses: int | None = None,  # None → len(gap_results) * _NUM_M3_RULES
        contracts: list[ContractContext] | None = None,
        detected_reliquidations: float = 0.0,
        year: int = 2026,
        reference_date: date | None = None,
    ) -> ExposureRequest:
        """
        Construye ExposureRequest derivando workers_at_risk y outdated_clauses
        directamente del output de M3, sin valores manuales.

        - workers_at_risk  = contratos con al menos 1 gap (cualquier severidad).
        - outdated_clauses = suma de gaps detectados en todos los contratos.
        - total_clauses    = len(gap_results) * _NUM_M3_RULES si no se especifica.
        """
        workers_at_risk = sum(1 for r in gap_results if r.get("gaps"))
        outdated_clauses = sum(len(r.get("gaps", [])) for r in gap_results)
        if total_clauses is None:
            total_clauses = len(gap_results) * _NUM_M3_RULES
        return cls(
            company_id=company_id,
            workers_at_risk=workers_at_risk,
            detected_reliquidations=detected_reliquidations,
            total_clauses=total_clauses,
            outdated_clauses=outdated_clauses,
            contracts=contracts or [],
            reference_date=reference_date,
            year=year,
        )


class ExposureService:
    def __init__(self, audit: AuditLog) -> None:
        self._audit = audit

    def compute(self, ctx: TenantContext, req: ExposureRequest) -> dict:
        """
        Computa número mágico + alertas. Función pura mediada por audit.
        Mismo req → mismo output (isolation_test del contrato M6).
        """
        magic = compute(ExposureInput(
            workers_at_risk=req.workers_at_risk,
            detected_reliquidations=req.detected_reliquidations,
            total_clauses=req.total_clauses,
            outdated_clauses=req.outdated_clauses,
            year=req.year,
        ))

        alerts = compute_alerts(req.contracts, reference_date=req.reference_date)

        self._audit.record(
            ctx,
            "exposure.compute",
            req.company_id,
            grounding=["M3.gaps", "M4.reliquidaciones"],
        )

        return {
            "company_id": req.company_id,
            "magic_number": {
                "outdated_clauses": magic.outdated_clauses,
                "pct_outdated": magic.pct_outdated,
                "cop_exposure": magic.cop_exposure,
                "exposure_formula": magic.formula,
                "constants": {
                    "SMLMV_2026": smlmv(req.year),
                    "mora_factor_art65": "1 dia salario por dia de mora",
                },
            },
            "alerts": [a.to_dict() for a in alerts],
        }
