"""
Cliente ElevenLabs + Twilio para la diligencia de descargos. (Dueño: David)

Port condensado de AFFIRMA: `tools/push_agent.py`, `tools/push_datacollection.py`,
`tools/twilio_call.py` e `src/ingest.py`. Hace cuatro cosas:

  1. configure_agent()   sube first_message + system_prompt (resueltos) al agente.
  2. configure_data_collection()  configura la extracción tipada post-llamada.
  3. place_call(to)      lanza la llamada saliente real (suena el teléfono).
  4. fetch_conversation(cid)  jala transcript + data_collection al terminar.

Todo se parametriza con `Settings` (.env). Sin credenciales -> error claro, nunca
una llamada silenciosa que parezca exitosa.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.adapters.telephony import descargos_agent as agent

EL_BASE = "https://api.elevenlabs.io/v1/convai"


class TelephonyError(RuntimeError):
    """Falla al hablar con ElevenLabs/Twilio (credenciales, red, API)."""


def _requests():
    """Import perezoso: el backend importa este módulo aunque `requests` no esté
    instalado (solo se necesita al hacer la llamada real)."""
    try:
        import requests  # noqa: PLC0415
    except ImportError as e:  # pragma: no cover
        raise TelephonyError("Falta el paquete 'requests' (pip install requests)") from e
    return requests


class ElevenLabsDescargosClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._s = settings or get_settings()

    # -- helpers --------------------------------------------------------------

    def _key(self) -> str:
        k = (self._s.elevenlabs_api_key or "").strip()
        if not k:
            raise TelephonyError("Falta ELEVENLABS_API_KEY en .env")
        return k

    def _agent_id(self) -> str:
        a = (self._s.elevenlabs_agent_id or "").strip()
        if not a:
            raise TelephonyError("Falta ELEVENLABS_AGENT_ID en .env")
        return a

    def _headers(self) -> dict:
        return {"xi-api-key": self._key(), "Content-Type": "application/json"}

    # -- 1) subir el prompt de descargos al agente ----------------------------

    def configure_agent(self, case: agent.DescargosCase) -> dict:
        """PATCH del first_message + system_prompt YA RESUELTOS (sin {{...}}), para
        que el agente público de demo arranque sin depender de dynamic variables."""
        requests = _requests()
        aid = self._agent_id()
        res = agent.resolved_prompts(case)
        g = requests.get(f"{EL_BASE}/agents/{aid}", headers=self._headers())
        if g.status_code >= 300:
            raise TelephonyError(f"GET agent falló: {g.status_code} {g.text[:200]}")
        cfg = g.json()
        conv = cfg.get("conversation_config") or {}
        ag = conv.get("agent") or {}
        ag["first_message"] = res["first_message"]
        ag["language"] = case.language
        pr = ag.get("prompt")
        if isinstance(pr, dict):
            pr["prompt"] = res["system_prompt"]
        else:
            ag["prompt"] = {"prompt": res["system_prompt"]}
        conv["agent"] = ag
        # ElevenLabs exige que los agentes en idioma no-inglés usen un modelo TTS
        # turbo/flash v2.5. Lo fijamos (preservando voice_id y demás ajustes).
        if (case.language or "en").lower() != "en":
            tts = conv.get("tts") or {}
            tts["model_id"] = "eleven_turbo_v2_5"
            conv["tts"] = tts
        r = requests.patch(f"{EL_BASE}/agents/{aid}", headers=self._headers(),
                           json={"conversation_config": conv})
        if r.status_code >= 300:
            raise TelephonyError(f"PATCH agent falló: {r.status_code} {r.text[:300]}")
        return {"agent_id": aid, "status": "configured"}

    # -- 2) configurar la extracción tipada -----------------------------------

    def configure_data_collection(self) -> dict:
        requests = _requests()
        aid = self._agent_id()
        g = requests.get(f"{EL_BASE}/agents/{aid}", headers=self._headers())
        if g.status_code >= 300:
            raise TelephonyError(f"GET agent falló: {g.status_code} {g.text[:200]}")
        cfg = g.json()
        ps = cfg.get("platform_settings") or {}
        ps["data_collection"] = {
            item["identifier"]: {"type": item["type"], "description": item["description"]}
            for item in agent.data_collection_schema()
        }
        r = requests.patch(f"{EL_BASE}/agents/{aid}", headers=self._headers(),
                           json={"platform_settings": ps})
        if r.status_code >= 300:
            raise TelephonyError(f"PATCH data_collection falló: {r.status_code} {r.text[:300]}")
        return {"agent_id": aid, "fields": [i["identifier"] for i in agent.data_collection_schema()]}

    # -- 3) la llamada saliente real ------------------------------------------

    def place_call(self, to_number: str) -> dict:
        """Lanza la llamada. El trabajador recibe la llamada y el agente conduce
        la diligencia. Devuelve conversation_id para luego jalar el resultado."""
        requests = _requests()
        pid = (self._s.elevenlabs_agent_phone_number_id or "").strip()
        if not pid:
            raise TelephonyError("Falta ELEVENLABS_AGENT_PHONE_NUMBER_ID (importa el número Twilio)")
        body = {
            "agent_id": self._agent_id(),
            "agent_phone_number_id": pid,
            "to_number": to_number,
        }
        r = requests.post(f"{EL_BASE}/twilio/outbound-call", headers=self._headers(), json=body)
        if r.status_code >= 300:
            raise TelephonyError(f"outbound-call falló: {r.status_code} {r.text[:300]}")
        data = r.json()
        return {"conversation_id": data.get("conversation_id"),
                "call_sid": data.get("callSid"), "to": to_number}

    # -- 4) jalar el resultado de la llamada ----------------------------------

    def fetch_conversation(self, conversation_id: str) -> dict:
        requests = _requests()
        r = requests.get(f"{EL_BASE}/conversations/{conversation_id}", headers=self._headers())
        if r.status_code >= 300:
            raise TelephonyError(f"GET conversation falló: {r.status_code} {r.text[:200]}")
        return r.json()
