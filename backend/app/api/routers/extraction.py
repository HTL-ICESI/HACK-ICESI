"""POST /api/extract — M2. Recibe {doc_id, text} y devuelve {doc_id, record} con cita."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.api.deps import get_extraction_service
from app.services.extraction_service import ExtractionService

router = APIRouter(prefix="/api", tags=["extraction"])


class ExtractRequest(BaseModel):
    doc_id: str
    text: str


@router.post("/extract")
async def extract_endpoint(
    req: ExtractRequest,
    ctx: TenantContext = Depends(get_tenant),
    svc: ExtractionService = Depends(get_extraction_service),
):
    record = await svc.extract(ctx, req.doc_id, req.text)
    return {"doc_id": req.doc_id, "record": record}
