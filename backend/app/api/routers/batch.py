"""
Batch — procesamiento masivo de contratos.

  POST /api/batch/ingest              recibe ZIP o múltiples archivos → batch_id
  GET  /api/batch/status/{batch_id}   progreso + summary por contrato (para polling)
  GET  /api/batch/result/{batch_id}/{doc_id}   análisis completo de un contrato

El procesamiento corre en background (asyncio); el frontend hace polling de /status.
"""
from __future__ import annotations

import io
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.api.deps import get_batch_service
from app.services.batch_service import BatchService

router = APIRouter(prefix="/api/batch", tags=["batch"])

_DOC_EXTS = (".txt", ".pdf", ".docx", ".xlsx", ".xls")


def _expand(uploads: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Expande ZIPs a sus archivos de contrato; deja pasar los archivos sueltos."""
    out: list[tuple[str, bytes]] = []
    for name, content in uploads:
        if name.lower().endswith(".zip"):
            try:
                zf = zipfile.ZipFile(io.BytesIO(content))
            except zipfile.BadZipFile:
                continue
            for inner in zf.namelist():
                if inner.startswith("__MACOSX") or inner.endswith("/"):
                    continue
                if inner.lower().endswith(_DOC_EXTS):
                    out.append((inner.split("/")[-1], zf.read(inner)))
        elif name.lower().endswith(_DOC_EXTS):
            out.append((name, content))
    return out


@router.post("/ingest")
async def ingest_batch(
    files: list[UploadFile] = File(...),
    ctx: TenantContext = Depends(get_tenant),
    svc: BatchService = Depends(get_batch_service),
):
    uploads = [(f.filename or "archivo", await f.read()) for f in files]
    expanded = _expand(uploads)
    if not expanded:
        raise HTTPException(status_code=400,
                            detail="No se encontraron contratos (.txt/.pdf/.docx) en la carga.")
    return svc.create_batch(ctx, expanded)


@router.get("/latest")
def batch_latest(
    ctx: TenantContext = Depends(get_tenant),
    svc: BatchService = Depends(get_batch_service),
):
    """Último lote analizado por la empresa (para revisitarlo al volver a /batch)."""
    res = svc.latest(ctx)
    if res is None:
        return {"batch_id": None, "total": 0, "completed": 0, "results": []}
    return res


@router.get("/status/{batch_id}")
def batch_status(
    batch_id: str,
    ctx: TenantContext = Depends(get_tenant),
    svc: BatchService = Depends(get_batch_service),
):
    res = svc.status(ctx, batch_id)
    if res is None:
        raise HTTPException(status_code=404, detail="batch_id no encontrado.")
    return res


@router.get("/result/{batch_id}/{doc_id}")
def batch_result(
    batch_id: str,
    doc_id: str,
    ctx: TenantContext = Depends(get_tenant),
    svc: BatchService = Depends(get_batch_service),
):
    res = svc.result(ctx, batch_id, doc_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Resultado no disponible (no existe o aún no termina).")
    return res
