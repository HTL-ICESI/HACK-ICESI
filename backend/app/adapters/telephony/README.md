# 📞 Agente de Descargos por Llamada (J1) — Motor 2 / La Joya · Dueño: David

> **Esto es el agente que LLAMA al trabajador y le hace rendir descargos por teléfono.**
> Voz (ElevenLabs Agents) + telefonía (Twilio), con patrón AFFIRMA. La llamada solo
> **conduce y captura**; el guardián determinista (`domain/disciplinary/guardian.py`)
> **decide** si hay nulidad. El LLM nunca decide.

## Qué hace (en una frase)
Configura un agente de voz que llama al trabajador, conduce la **diligencia de descargos**
siguiendo los **7 pasos del debido proceso** (art. 29 CN + art. 115 CST reformado +
Circular MinTrabajo 0048/2026), captura señales tipadas, y construye el `DiligenceState`
que evalúa el guardián (J3) → si procede, se generan los documentos (J4).

## Archivos de esta carpeta
| Archivo | Rol |
|---|---|
| `descargos_agent.py` | **El guion**: first message + system prompt (7 pasos) + data collection (14 campos) + tool webhook. Port de AFFIRMA `agent_config.py`. |
| `elevenlabs_client.py` | Sube el agente, configura la extracción, **lanza la llamada** y jala el resultado. |
| `mapping.py` | Convierte lo capturado en la llamada → `DiligenceState` del guardián. |

## Endpoints (en `app/api/routers/disciplinary.py`)
- `POST /api/disciplinary/call` — lanza la llamada de descargos al trabajador.
- `POST /api/disciplinary/call/webhook` — post-llamada: arma el estado y corre el guardián.

## Cómo operarlo (CLI)
Ver **`backend/TASKS/J1-llamada-descargos.md`** (runbook completo) y `backend/tools/descargos_cli.py`:
```
python tools/descargos_cli.py check          # verifica Twilio
python tools/descargos_cli.py import-number   # importa el número Twilio -> phone_number_id
python tools/descargos_cli.py setup           # sube el guion + extracción al agente
python tools/descargos_cli.py call --to +57XXXXXXXXXX   # ¡llama!
python tools/descargos_cli.py conv --id <id>  # transcripción + veredicto del guardián
```

## Estado
✅ **Probado en vivo** (llamada real saliente a Colombia conectada y conducida).
Requiere credenciales en `backend/.env` (bloque J1) — ver `.env.example`.

## Regla de oro
El agente **conduce y captura**; el guardián (código puro) **decide**. Ningún booleano del
checklist lo decide el LLM. Eso es lo que el jurado audita como confiabilidad.
