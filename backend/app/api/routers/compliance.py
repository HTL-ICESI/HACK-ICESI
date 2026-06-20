"""POST /api/compliance/analyze — M3. Cruza un DocumentRecord contra el corpus normativo."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.api.deps import get_compliance_service
from app.services.compliance_service import ComplianceService
from app.domain.models import DocumentRecord

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


class AnalyzeRequest(BaseModel):
    doc_id: str
    record: DocumentRecord
    doc_type: str = "contrato"


@router.post("/analyze")
async def analyze_endpoint(
    req: AnalyzeRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: ComplianceService = Depends(get_compliance_service),
):
    return svc.analyze(ctx, req.doc_id, req.record, req.doc_type)
