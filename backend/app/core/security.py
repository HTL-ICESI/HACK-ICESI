"""
Seguridad: autenticación por API key -> resuelve el TenantContext.

Defensa en profundidad: aquí se autentica y se fija el tenant; el repository
vuelve a verificar el scoping (adapters/storage/repository). Datos PII del
trabajador (flujo disciplinario) se marcan para minimización (Ley 1581).
"""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.core.tenancy import TenantContext


async def get_tenant(authorization: str | None = Header(default=None)) -> TenantContext:
    """Dependencia FastAPI: 'Authorization: Bearer <api_key>' -> TenantContext."""
    settings = get_settings()
    token = (authorization or "").removeprefix("Bearer ").strip()
    tenant_id = settings.api_key_map.get(token)
    if not tenant_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key inválida o ausente.")
    return TenantContext(tenant_id=tenant_id, actor=f"key:{token[:6]}…")
