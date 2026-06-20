"""Configuración central (pydantic-settings). Única fuente de verdad de parámetros."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    # Fallback OpenAI-compatible (Infermatic / TotalGPT) — usado cuando no hay Anthropic key.
    infermatic_api_key: str = ""
    infermatic_base_url: str = "https://api.totalgpt.ai"
    infermatic_model: str = "Qwen-Qwen3.6-35B-A3B"

    tesseract_cmd: str = ""
    # "key:tenant_id,key2:tenant_id2" -> se parsea a dict en api_key_map
    api_keys: str = "demo-hg-key:empresa-001"
    param_year: int = 2026

    # --- J1 Telefonía de descargos (ElevenLabs Agents + Twilio, patrón AFFIRMA) ---
    # Sin estas variables el resto del backend funciona igual; solo se inhabilita /call.
    elevenlabs_api_key: str = ""
    elevenlabs_agent_id: str = ""              # agente "Descargos HG"
    elevenlabs_agent_phone_number_id: str = ""  # número Twilio importado a ElevenLabs
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""              # número saliente, E.164
    # --- WhatsApp de evidencia (Twilio Messaging) ---
    twilio_whatsapp_from: str = "whatsapp:+14155238886"  # sandbox por defecto
    backend_host: str = ""                     # host público (cloudflared) para webhooks/media
    hg_backend_token: str = ""                 # secreto compartido del webhook submit_descargos

    @property
    def api_key_map(self) -> dict[str, str]:
        """Mapa api_key -> tenant_id. En prod esto es una tabla; aquí basta el .env."""
        out: dict[str, str] = {}
        for pair in filter(None, (p.strip() for p in self.api_keys.split(","))):
            key, _, tenant = pair.partition(":")
            if key and tenant:
                out[key] = tenant
        return out


@lru_cache
def get_settings() -> Settings:
    return Settings()
