"""
Multitenancy: el contexto de tenant es ciudadano de primera clase.

Cada empresa cliente de HG es un TENANT con datos aislados. El TenantContext se
resuelve desde la API key y se propaga por inyección de dependencia. Ningún
service ni repository opera sin un tenant_id válido (ver core/security y
adapters/storage/repository).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    """Identidad del tenant para la petición en curso. Inmutable."""
    tenant_id: str          # empresa cliente, p.ej. "empresa-001"
    org_id: str = "hurtado-gandini"   # la firma dueña del cerebro
    actor: str = "system"   # quién ejecuta (para audit trail)

    def require(self) -> str:
        if not self.tenant_id:
            raise PermissionError("Operación sin tenant_id: acceso denegado.")
        return self.tenant_id


class TenantViolation(PermissionError):
    """Se intentó acceder a datos de otro tenant. Nunca debe llegar al cliente con data."""
