"""
POST /api/company/analyze — Orquestador. Sube los documentos de una empresa
(varios archivos o un ZIP); corre la pipeline completa y devuelve el dashboard
con el número mágico REAL derivado de los contratos (no un demo fijo).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.api.deps import get_company_service
from app.services.company_service import CompanyService

router = APIRouter(prefix="/api/company", tags=["company"])


@router.post("/analyze")
async def analyze_company(
    files: list[UploadFile] = File(..., description="Contratos (PDF/DOCX) y/o nómina (CSV). Acepta un .zip."),
    ctx: TenantContext = Depends(get_tenant),
    svc: CompanyService = Depends(get_company_service),
):
    payload = [(f.filename or "sin_nombre", await f.read()) for f in files]
    return await svc.analyze_company(ctx, payload)


@router.get("/history")
def company_history(
    ctx: TenantContext = Depends(get_tenant),
    svc: CompanyService = Depends(get_company_service),
):
    """Contratos y gaps persistidos en la BD para esta empresa (scoped por tenant)."""
    return svc.history(ctx)
