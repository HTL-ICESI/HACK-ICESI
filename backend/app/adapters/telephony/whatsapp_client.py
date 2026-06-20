"""
Cliente Twilio WhatsApp — envía al trabajador la evidencia + un párrafo de contexto
antes de la diligencia de descargos. (Patrón AFFIRMA `app.py::send_whatsapp`.)

Degradación honesta: sin credenciales NO finge un envío. `configured()` es False y
el service devuelve un *preview* del mensaje (lo que se enviaría) en vez de un éxito
silencioso. Con credenciales, pega a la Messages API real de Twilio.
"""
from __future__ import annotations

import re

from app.config import Settings, get_settings

TW_BASE = "https://api.twilio.com/2010-04-01"


class WhatsAppError(RuntimeError):
    """Falla al hablar con Twilio (credenciales, red, API)."""


def _requests():
    try:
        import requests  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover
        raise WhatsAppError("Falta el paquete 'requests' (pip install requests)") from e
    return requests


def normalize_co(number: str) -> str:
    """E.164 best-effort para un celular colombiano (port de AFFIRMA)."""
    d = re.sub(r"\D", "", number or "")
    if len(d) == 10 and d.startswith("3"):
        return "+57" + d
    if d.startswith("57") and len(d) == 12:
        return "+" + d
    if d:
        return "+" + d
    return ""


class TwilioWhatsAppClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._s = settings or get_settings()

    def configured(self) -> bool:
        return bool((self._s.twilio_account_sid or "").strip()
                    and (self._s.twilio_auth_token or "").strip())

    def send(self, to_e164: str, *, body: str | None = None,
             media_urls: list[str] | None = None) -> dict:
        """Envía un WhatsApp. `media_urls` deben ser URLs PÚBLICAS (Twilio las descarga)."""
        if not self.configured():
            raise WhatsAppError("Faltan TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN en .env")
        requests = _requests()
        sid = self._s.twilio_account_sid
        tok = self._s.twilio_auth_token
        # Twilio exige que From y To sean del mismo canal: ambos con prefijo
        # "whatsapp:". Normalizamos el From por si en .env viene sin él (error 21910).
        sender = (self._s.twilio_whatsapp_from or "").strip()
        from_ = sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}"
        data: dict = {"From": from_, "To": f"whatsapp:{to_e164}"}
        if body:
            data["Body"] = body
        # Twilio acepta varias MediaUrl como MediaUrl (repetido); requests serializa listas.
        if media_urls:
            data["MediaUrl"] = media_urls
        r = requests.post(f"{TW_BASE}/Accounts/{sid}/Messages.json",
                          auth=(sid, tok), data=data)
        if r.status_code >= 300:
            raise WhatsAppError(f"Twilio Messages falló: {r.status_code} {r.text[:300]}")
        out = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return {"sid": out.get("sid"), "status": out.get("status"), "to": to_e164}
