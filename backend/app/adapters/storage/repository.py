"""
Repositorio tenant-scoped. SEGUNDA capa de aislamiento multitenant.

Toda lectura/escritura exige tenant_id y rechaza el cruce de tenants. Implementación
en memoria para el hackathon; la interfaz permite cambiar a Postgres (row-level
security) sin tocar services ni domain.
"""
from __future__ import annotations

from collections import defaultdict

from app.core.tenancy import TenantContext, TenantViolation


class InMemoryRepository:
    """Almacén key-value namespaced por tenant. Defensa en profundidad."""

    def __init__(self) -> None:
        # {tenant_id: {collection: {id: obj}}}
        self._db: dict[str, dict[str, dict[str, object]]] = defaultdict(lambda: defaultdict(dict))

    def put(self, ctx: TenantContext, collection: str, key: str, value: object) -> None:
        self._db[ctx.require()][collection][key] = value

    def get(self, ctx: TenantContext, collection: str, key: str) -> object | None:
        return self._db[ctx.require()][collection].get(key)

    def list(self, ctx: TenantContext, collection: str) -> list[object]:
        return list(self._db[ctx.require()][collection].values())

    def assert_owned(self, ctx: TenantContext, collection: str, key: str) -> None:
        """Verifica que el recurso pertenece al tenant. Lanza si hay cruce."""
        if key not in self._db[ctx.require()][collection]:
            raise TenantViolation(f"Recurso {collection}/{key} no pertenece a {ctx.tenant_id}.")


# Singleton de proceso (en prod -> sesión/conexión por request)
repository = InMemoryRepository()
