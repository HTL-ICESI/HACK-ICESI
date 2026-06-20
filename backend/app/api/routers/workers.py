"""
/api/workers — registro de contactos de trabajadores por tenant.

RRHH rellena el celular de cada trabajador (el OCR no extrae teléfonos de los
contratos). El `doc_id` coincide con el BatchItem.doc_id del pipeline M1→M5.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_tenant
from app.core.tenancy import TenantContext
from app.db.base import SessionLocal
from app.db.models import WorkerContact

router = APIRouter(prefix="/api/workers", tags=["workers"])


class WorkerContactOut(BaseModel):
    doc_id: str
    nombre: str
    phone: str


class PhonePatch(BaseModel):
    phone: str
    nombre: str = ""


@router.get("", response_model=list[WorkerContactOut])
def list_workers(ctx: TenantContext = Depends(get_tenant)):
    """Lista todos los contactos del tenant (doc_id + nombre + phone)."""
    with SessionLocal() as db:
        rows = db.query(WorkerContact).filter(
            WorkerContact.tenant_id == ctx.tenant_id
        ).all()
        return [WorkerContactOut(doc_id=r.doc_id, nombre=r.nombre, phone=r.phone)
                for r in rows]


@router.patch("/{doc_id}/phone", response_model=WorkerContactOut)
def update_phone(
    doc_id: str,
    body: PhonePatch,
    ctx: TenantContext = Depends(get_tenant),
):
    """Crea o actualiza el número de WhatsApp de un trabajador."""
    with SessionLocal() as db:
        row = db.query(WorkerContact).filter(
            WorkerContact.tenant_id == ctx.tenant_id,
            WorkerContact.doc_id == doc_id,
        ).first()
        if row is None:
            row = WorkerContact(
                tenant_id=ctx.tenant_id,
                doc_id=doc_id,
                nombre=body.nombre,
                phone=body.phone,
            )
            db.add(row)
        else:
            row.phone = body.phone
            if body.nombre:
                row.nombre = body.nombre
        db.commit()
        db.refresh(row)
        return WorkerContactOut(doc_id=row.doc_id, nombre=row.nombre, phone=row.phone)


@router.post("/upsert-batch", response_model=list[WorkerContactOut])
def upsert_batch_contacts(
    workers: list[WorkerContactOut],
    ctx: TenantContext = Depends(get_tenant),
):
    """Registra nombres del lote (sin phone) para que el roster esté en BD desde M5."""
    results = []
    with SessionLocal() as db:
        for w in workers:
            row = db.query(WorkerContact).filter(
                WorkerContact.tenant_id == ctx.tenant_id,
                WorkerContact.doc_id == w.doc_id,
            ).first()
            if row is None:
                row = WorkerContact(
                    tenant_id=ctx.tenant_id,
                    doc_id=w.doc_id,
                    nombre=w.nombre,
                    phone=w.phone or "",
                )
                db.add(row)
            else:
                if w.nombre:
                    row.nombre = w.nombre
                # NO sobreescribir phone si ya existe
                if w.phone and not row.phone:
                    row.phone = w.phone
            results.append(row)
        db.commit()
        return [WorkerContactOut(doc_id=r.doc_id, nombre=r.nombre, phone=r.phone)
                for r in results]
