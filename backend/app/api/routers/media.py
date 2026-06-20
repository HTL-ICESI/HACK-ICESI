"""
Endpoint PÚBLICO de evidencia para que Twilio descargue los adjuntos de WhatsApp.

No lleva auth de tenant (Twilio no manda API key): el acceso se controla con el
token HMAC `t` que firma (tenant_id, evidence_id). Sin token válido -> 403. El
tenant se recupera del propio token, así que no se cruza información entre empresas.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response

from app.api.deps import get_pipeline_service
from app.core.media_token import verify
from app.core.tenancy import TenantContext

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/evidence/{evidence_id}")
def get_evidence_media(evidence_id: str, t: str = Query(..., description="token HMAC firmado")):
    tenant_id = verify(t, evidence_id)
    if not tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token de media inválido o ausente.")
    ctx = TenantContext(tenant_id=tenant_id, actor="media:twilio")
    blob = get_pipeline_service().get_evidence_blob(ctx, evidence_id)
    if not blob:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidencia no encontrada.")
    return Response(
        content=blob["bytes"],
        media_type=blob["content_type"],
        headers={"Content-Disposition": f'inline; filename="{blob["filename"]}"'},
    )
