"""
M4 service — orquesta el motor determinista de liquidación + persistencia tenant-scoped
+ audit. La lógica de cálculo vive en domain (puro); aquí solo se coordina.
"""
from __future__ import annotations

from app.core.tenancy import TenantContext
from app.core.audit import AuditLog
from app.domain.liquidation.engine import LiquidationInput, LiquidationResult, liquidate


class LiquidationService:
    def __init__(self, audit: AuditLog) -> None:
        self._audit = audit

    def compute(self, ctx: TenantContext, doc_id: str, inp: LiquidationInput) -> LiquidationResult:
        result = liquidate(inp)                       # dominio puro, determinista
        self._audit.record(ctx, "liquidation.compute", doc_id, grounding=["CST art. 249,306,186,64"])
        return result
