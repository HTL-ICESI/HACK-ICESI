"""
Tokens firmados (HMAC-SHA256) para las URLs públicas de evidencia.

Twilio descarga los adjuntos de WhatsApp desde una URL pública, SIN cabecera de
autenticación de tenant. Para no exponer el endpoint de media a cualquiera, cada
URL lleva un token `t` que firma (tenant_id, evidence_id) con un secreto del .env.
El endpoint verifica la firma antes de devolver bytes, y de paso recupera a qué
tenant pertenece el archivo (sin necesidad de la API key).

El secreto es HG_BACKEND_TOKEN; si está vacío cae a TWILIO_AUTH_TOKEN (siempre
presente cuando hay envío real), para que funcione en el demo sin config extra.
"""
from __future__ import annotations

import base64
import hashlib
import hmac

from app.config import get_settings


class MediaTokenError(RuntimeError):
    """No hay secreto para firmar/verificar las URLs de media."""


def _secret() -> bytes:
    s = get_settings()
    raw = (s.hg_backend_token or "").strip() or (s.twilio_auth_token or "").strip()
    if not raw:
        raise MediaTokenError(
            "Falta HG_BACKEND_TOKEN (o TWILIO_AUTH_TOKEN) para firmar las URLs de media"
        )
    return raw.encode()


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _mac(tenant_id: str, evidence_id: str) -> bytes:
    return hmac.new(_secret(), f"{tenant_id}:{evidence_id}".encode(), hashlib.sha256).digest()


def sign(tenant_id: str, evidence_id: str) -> str:
    """Token opaco `<b64(tenant)>.<b64(hmac)>` para colgar como query `t`."""
    return f"{_b64(tenant_id.encode())}.{_b64(_mac(tenant_id, evidence_id))}"


def verify(token: str, evidence_id: str) -> str | None:
    """Devuelve el tenant_id si el token es válido para esa evidencia; si no, None."""
    try:
        tpart, spart = (token or "").split(".", 1)
        tenant_id = _unb64(tpart).decode()
        got = _unb64(spart)
    except (ValueError, UnicodeDecodeError, base64.binascii.Error):
        return None
    return tenant_id if hmac.compare_digest(_mac(tenant_id, evidence_id), got) else None
