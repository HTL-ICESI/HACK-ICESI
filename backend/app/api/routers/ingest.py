"""POST /api/ingest — M1. Recibe un archivo (multipart) y devuelve texto + confianza + status."""
from __future__ import annotations

import pathlib
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.api.deps import get_ingest_service
from app.services.ingest_service import IngestService

router = APIRouter(prefix="/api", tags=["ingest"])

SUPPORTED = (".txt", ".pdf", ".docx", ".docm", ".xlsx", ".xls")

_DEMO_FILE = pathlib.Path(__file__).parents[3] / "data" / "contrato_hg_ejemplo.txt"


@router.post("/ingest")
async def ingest_endpoint(
    file: Optional[UploadFile] = File(default=None),
    ctx: TenantContext = Depends(get_tenant),
    svc: IngestService = Depends(get_ingest_service),
):
    if file is None or not file.filename:
        # Sin archivo → usar el contrato demo (degradación honesta para el demo)
        content = _DEMO_FILE.read_bytes()
        filename = _DEMO_FILE.name
    else:
        content = await file.read()
        filename = file.filename

    doc_id = filename.rsplit(".", 1)[0]
    try:
        result = svc.ingest_document(ctx, doc_id, content, filename)
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Formato no soportado. Use uno de: {', '.join(SUPPORTED)}.",
        )
    return {"doc_id": result.doc_id, "text": result.text,
            "confidence": result.confidence, "status": result.status}
