"""POST /api/remediation/generate — M5. Dado un gap + cifras del motor, genera el documento correctivo."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.api.deps import get_remediation_service
from app.domain.models import DocumentRecord
from app.services.remediation_service import RemediationService

router = APIRouter(prefix="/api/remediation", tags=["remediation"])

_VALID_GAP_IDS = {"g1", "g2", "g3", "g4", "g5"}
_VALID_DOC_TYPES = {"otrosi", "instruccion_nomina", "acta_terminacion", "contrato_corregido"}


class RemediationRequest(BaseModel):
    doc_id: str
    gap: dict                       # gap serializado (gap_id, issue, severity, norm, remedy_type)
    liquidation: dict | None = None # LiquidationResult serializado de M4 (puede ser null)
    doc_type: str                   # otrosi | instruccion_nomina | acta_terminacion | contrato_corregido
    record: DocumentRecord | None = None  # DocumentRecord de M2 — necesario para personalizar el documento

    @field_validator("gap")
    @classmethod
    def gap_id_must_be_known(cls, v: dict) -> dict:
        gap_id = v.get("gap_id", "")
        if gap_id not in _VALID_GAP_IDS:
            raise ValueError(f"gap_id {gap_id!r} no reconocido. Valores válidos: {sorted(_VALID_GAP_IDS)}")
        return v

    @field_validator("doc_type")
    @classmethod
    def doc_type_must_be_known(cls, v: str) -> str:
        if v not in _VALID_DOC_TYPES:
            raise ValueError(f"doc_type {v!r} no reconocido. Valores válidos: {sorted(_VALID_DOC_TYPES)}")
        return v


@router.post("/generate")
async def generate_endpoint(
    req: RemediationRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: RemediationService = Depends(get_remediation_service),
):
    return await svc.generate(
        ctx, req.doc_id, req.gap, req.liquidation, req.doc_type, req.record
    )
