# TAREA — J1: Llamada de descargos (telefonía) · Dueño: David

> Port del patrón **AFFIRMA** (repo Due-Legal). Un agente de voz ElevenLabs llama al
> trabajador, conduce la diligencia de descargos por el debido proceso, captura señales
> tipadas, y el **guardián (J3) decide** si hay nulidad. El agente NUNCA decide.

## Qué quedó construido (slice aislado, sin credenciales)

| Pieza | Archivo | Equivalente en AFFIRMA |
|---|---|---|
| Config del agente (prompt debido proceso + extracción) | `app/adapters/telephony/descargos_agent.py` | `src/agent_config.py` |
| Cliente EL/Twilio (subir agente, llamar, jalar resultado) | `app/adapters/telephony/elevenlabs_client.py` | `tools/push_agent.py` + `push_datacollection.py` + `twilio_call.py` + `src/ingest.py` |
| Mapeo llamada → `DiligenceState` | `app/adapters/telephony/mapping.py` | `src/ingest.py::extract_fields` |
| Veredicto determinista | `app/domain/disciplinary/guardian.py` (ya existía) | `src/state_machine.py` |
| Endpoints `/call` y `/call/webhook` | `app/api/routers/disciplinary.py` | `app.py` (webhook/poller) |
| Prueba aislada (sin red) | `tests/adapters/test_telephony.py` | `tests/test_state_machine.py` |

**Tests:** `python -m pytest tests/adapters/test_telephony.py -q` → verde (6 casos).
La llamada en vivo NO se prueba en CI; se prueba a mano con credenciales (abajo).

## Flujo

```
POST /api/disciplinary/call            → configura el agente para este caso + LLAMA al trabajador
   (el agente conduce la diligencia: identidad+derecho a acompañante → cargos →
    pruebas → descargos → cierre+término)
ElevenLabs → POST /api/disciplinary/call/webhook   (al cerrar, manda lo capturado)
   → mapping arma DiligenceState → guardián (J3) → ¿nulidad? → (J4 genera docs si procede)
```

## Setup de credenciales (una vez)

1. Copia `.env.example` → `.env` y llena el bloque **J1 Telefonía**:
   `ELEVENLABS_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.
2. Crea un agente en el dashboard de ElevenLabs (Conversational AI) y copia su id →
   `ELEVENLABS_AGENT_ID`.
3. Importa el número Twilio a ElevenLabs para obtener `agent_phone_number_id`. (Mismo
   request que `twilio_call.py import-number`: `POST /v1/convai/phone-numbers` con provider
   twilio + sid + token + phone_number.) Guárdalo en `ELEVENLABS_AGENT_PHONE_NUMBER_ID`.
4. Para el webhook: expón el backend con un túnel (cloudflared) y pon el host público en
   `BACKEND_HOST`; define un secreto en `HG_BACKEND_TOKEN` (el tool del agente lo manda en
   `X-HG-Secret`).

> **Trial de Twilio:** el número destino debe estar **verificado** (Console → Verified Caller
> IDs). Revisa el permiso de marcación a Colombia (`DialingPermissions/Countries/CO`), igual
> que `twilio_call.py diag`.

## Probar la llamada real

```bash
uvicorn app.main:app --reload          # backend arriba
# en otra terminal (con tu API key de tenant):
curl -X POST http://127.0.0.1:8000/api/disciplinary/call \
  -H "Authorization: Bearer demo-hg-key" -H "Content-Type: application/json" \
  -d '{"session_id":"desc-001","to_number":"+57XXXXXXXXXX",
       "company_name":"Empresa Cliente SAS","worker_name":"Pedro Pérez",
       "charges_summary":"El 12/05/2026 se ausentó sin excusa...",
       "evidence_summary":"Registro de acceso, reporte del jefe...",
       "response_deadline":"cinco (5) días hábiles"}'
```

El teléfono suena, el agente conduce la diligencia, y al cerrar dispara el webhook que
corre el guardián.

## Pendiente / siguiente

- [ ] David: validar el **guion del debido proceso** en `descargos_agent.py::SYSTEM_PROMPT`
      contra art. 29 CN + art. 115 CST + Código Procesal del Trabajo (¿falta un paso? ¿orden?).
- [ ] Cómputo determinista de `term_respected` (fechas citación vs. término) — hoy entra como
      override; conviene calcularlo en el backend, no confiarlo a la llamada.
- [ ] Conectar J4 (generar acta de descargos) al resultado del webhook.
- [ ] **Demo-safe:** grabar una llamada exitosa de respaldo. La llamada en vivo es frágil
      (igual que la voz en `J2`); narrar + reproducir si la red falla.

## Regla de oro
El agente CONDUCE y CAPTURA; el guardián (código puro) DECIDE. Ningún booleano del checklist
lo decide el LLM. Eso es lo que el jurado audita como confiabilidad.
