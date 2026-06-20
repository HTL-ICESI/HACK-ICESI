"""
Repositorio tenant-scoped sobre la BD. Misma garantía que el in-memory: ninguna
operación cruza tenants. Fija `tenant_id` al escribir y filtra por él al leer.
"""
from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session

from app.core.tenancy import TenantContext, TenantViolation
from app.db.base import Base

T = TypeVar("T", bound=Base)


class TenantRepository:
    """Envuelve una Session y la ata a un tenant. Todo acceso queda namespaced."""

    def __init__(self, session: Session, ctx: TenantContext) -> None:
        self._db = session
        self._tenant = ctx.require()

    def add(self, entity: T) -> T:
        """Inserta forzando el tenant_id del contexto (ignora el que traiga el objeto)."""
        entity.tenant_id = self._tenant  # type: ignore[attr-defined]
        self._db.add(entity)
        self._db.commit()
        self._db.refresh(entity)
        return entity

    def get(self, model: type[T], pk: int) -> T | None:
        """Lee por PK SOLO si pertenece al tenant; si es de otro -> None (no se filtra)."""
        obj = self._db.get(model, pk)
        if obj is None or getattr(obj, "tenant_id", None) != self._tenant:
            return None
        return obj

    def list(self, model: type[T]) -> list[T]:
        """Lista todas las filas del tenant para ese modelo."""
        return list(self._db.query(model).filter_by(tenant_id=self._tenant).all())

    def assert_owned(self, model: type[T], pk: int) -> T:
        """Devuelve la entidad o lanza TenantViolation si no es del tenant."""
        obj = self.get(model, pk)
        if obj is None:
            raise TenantViolation(f"{model.__name__}#{pk} no pertenece a {self._tenant}.")
        return obj
