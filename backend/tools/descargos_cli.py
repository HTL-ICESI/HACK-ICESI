"""
CLI para configurar y operar el agente de descargos en ElevenLabs + Twilio.
Port del patrón AFFIRMA `tools/twilio_call.py`, usando nuestro cliente.

Lee credenciales de `backend/.env` (vía app.config.Settings). Subcomandos:

  python tools/descargos_cli.py check           verifica credenciales Twilio + caller IDs verificados
  python tools/descargos_cli.py import-number    importa el número Twilio a ElevenLabs -> phone_number_id
  python tools/descargos_cli.py setup            sube el prompt de descargos + configura data collection
  python tools/descargos_cli.py diag             permiso de marcación a Colombia + últimas llamadas/errores
  python tools/descargos_cli.py call --to +57XXXXXXXXXX   lanza la llamada (suena el teléfono)
  python tools/descargos_cli.py conv --id <conversation_id>   trae transcript + veredicto del guardián

Ejecuta desde `cerebro-laboral-hg/backend/` con el venv activo.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permite ejecutar como script suelto (añade backend/ al path).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests  # noqa: E402

from app.config import get_settings                                   # noqa: E402
from app.adapters.telephony.elevenlabs_client import (                # noqa: E402
    ElevenLabsDescargosClient, TelephonyError, EL_BASE,
)
from app.adapters.telephony import descargos_agent as agent           # noqa: E402
from app.adapters.telephony.mapping import diligence_state_from_conversation  # noqa: E402
from app.domain.disciplinary.guardian import evaluate                 # noqa: E402

TW_BASE = "https://api.twilio.com/2010-04-01"
S = get_settings()


def _tw_auth() -> tuple[str, str]:
    if not (S.twilio_account_sid and S.twilio_auth_token):
        sys.exit("Faltan TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN en .env")
    return S.twilio_account_sid, S.twilio_auth_token


def cmd_check(_args) -> None:
    sid, tok = _tw_auth()
    a = requests.get(f"{TW_BASE}/Accounts/{sid}.json", auth=(sid, tok))
    print("Twilio account:", a.status_code, a.json().get("status") if a.ok else a.text[:200])
    cids = requests.get(f"{TW_BASE}/Accounts/{sid}/OutgoingCallerIds.json", auth=(sid, tok))
    verified = [c["phone_number"] for c in (cids.json().get("outgoing_caller_ids", []) if cids.ok else [])]
    print("Caller IDs verificados (llamables en trial):", verified or "(ninguno)")
    nums = requests.get(f"{TW_BASE}/Accounts/{sid}/IncomingPhoneNumbers.json", auth=(sid, tok))
    print("Números Twilio propios:", [n.get("phone_number") for n in
          (nums.json().get("incoming_phone_numbers", []) if nums.ok else [])])


def cmd_import_number(_args) -> None:
    if not S.elevenlabs_api_key:
        sys.exit("Falta ELEVENLABS_API_KEY en .env")
    body = {
        "provider": "twilio",
        "phone_number": S.twilio_phone_number,
        "label": "Descargos HG",
        "sid": S.twilio_account_sid,
        "token": S.twilio_auth_token,
    }
    r = requests.post(f"{EL_BASE}/phone-numbers",
                      headers={"xi-api-key": S.elevenlabs_api_key, "Content-Type": "application/json"},
                      json=body)
    print("import-number:", r.status_code)
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
    pid = data.get("phone_number_id") or (data.get("phone_number", {}) or {}).get("phone_number_id")
    if pid:
        print(f"\n>>> Pega esto en backend/.env:\nELEVENLABS_AGENT_PHONE_NUMBER_ID={pid}")


def cmd_setup(_args) -> None:
    client = ElevenLabsDescargosClient(S)
    case = agent.sample_case()
    try:
        print("Subiendo prompt de descargos…", client.configure_agent(case))
        print("Configurando data collection…", client.configure_data_collection())
        print("OK — agente listo. Verifica en el dashboard de ElevenLabs.")
    except TelephonyError as e:
        sys.exit(f"ERROR: {e}")


def cmd_diag(_args) -> None:
    sid, tok = _tw_auth()
    geo = requests.get(f"https://voice.twilio.com/v1/DialingPermissions/Countries/CO", auth=(sid, tok))
    if geo.ok:
        g = geo.json()
        print(f"Permiso marcación CO: low_risk={g.get('low_risk_numbers_enabled')} "
              f"high_risk_special={g.get('high_risk_special_numbers_enabled')}")
    else:
        print("Permiso CO:", geo.status_code, geo.text[:200])
    calls = requests.get(f"{TW_BASE}/Accounts/{sid}/Calls.json?PageSize=5", auth=(sid, tok))
    print("--- últimas llamadas ---")
    for c in (calls.json().get("calls", []) if calls.ok else []):
        print(f"{c.get('to')} | {c.get('status')} | dur={c.get('duration')} | {c.get('start_time')}")
    notif = requests.get(f"{TW_BASE}/Accounts/{sid}/Notifications.json?PageSize=5", auth=(sid, tok))
    print("--- errores/notificaciones ---")
    for n in (notif.json().get("notifications", []) if notif.ok else []):
        print(f"code={n.get('error_code')} | {(n.get('message_text') or '')[:160]}")


def cmd_call(args) -> None:
    client = ElevenLabsDescargosClient(S)
    try:
        res = client.place_call(args.to)
        print("Llamando…", json.dumps(res, ensure_ascii=False))
        print("Cuando termine: python tools/descargos_cli.py conv --id", res.get("conversation_id"))
    except TelephonyError as e:
        sys.exit(f"ERROR: {e}")


def cmd_conv(args) -> None:
    client = ElevenLabsDescargosClient(S)
    conv = client.fetch_conversation(args.id)
    md = conv.get("metadata", {}) or {}
    print(f"status: {conv.get('status')}  has_audio: {conv.get('has_audio')}  "
          f"dur: {md.get('call_duration_secs')}s")
    for t in (conv.get("transcript") or []):
        msg = (t.get("message") or "").strip()
        if msg:
            print(f"[{t.get('role')}] {msg}")
    state = diligence_state_from_conversation(conv)
    verdict = evaluate(state)
    print("\n--- GUARDIÁN (determinista) ---")
    print("diligence_state:", state.__dict__)
    print("nullity_alert:", verdict.nullity_alert, "| can_proceed:", verdict.can_proceed)
    for m in verdict.missing_steps:
        print(f"  FALTA: {m.step} ({m.norm}) -> {m.consequence}")


def main() -> None:
    p = argparse.ArgumentParser(description="Configura/opera el agente de descargos (ElevenLabs+Twilio)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    sub.add_parser("import-number").set_defaults(func=cmd_import_number)
    sub.add_parser("setup").set_defaults(func=cmd_setup)
    sub.add_parser("diag").set_defaults(func=cmd_diag)
    c = sub.add_parser("call")
    c.add_argument("--to", required=True, help="número destino E.164, ej. +57XXXXXXXXXX")
    c.set_defaults(func=cmd_call)
    cv = sub.add_parser("conv")
    cv.add_argument("--id", required=True)
    cv.set_defaults(func=cmd_conv)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
