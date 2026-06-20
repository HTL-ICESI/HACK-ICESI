# TAREA — J2: Transcripción de descargos (la joya) · Dueño: David

> Lee primero: `AGENT-ONBOARDING.md`, `icesi-playbook/contracts.json` (bloque J2).
> Trabaja en `feat/joya-j2-transcripcion`.

## Qué hace J2
Toma el audio de la diligencia de descargos y devuelve la transcripción con segmentos
(timestamps). Es la entrada de datos del Motor 2.

## Dónde va el código
- Adapter → `app/adapters/transcription/whisper_client.py` (EXISTE como stub, complétalo).
- Service → `app/services/disciplinary_service.py` (EXISTE, método `transcribe_session`).
- Router → `app/api/routers/disciplinary.py` (EXISTE; añade `POST /api/disciplinary/transcribe`).

## Implementación
Usa Whisper (o `faster-whisper` para velocidad local). Entrada: bytes de audio (wav/mp3).
Salida: `{transcript, segments[]}` con la shape de `contracts.json` J2.

## Regla de oro
Sin audio o audio vacío → error claro, NUNCA un transcript inventado.

## Demo (importante)
La transcripción en vivo es frágil. Ten un **audio semilla pre-grabado** + su transcript de
respaldo, para que la demo corra aunque el micrófono falle.

## Tests obligatorios
- Audio semilla → transcript no vacío con segmentos.
- Audio vacío → error, no transcript inventado.

## Criterios de aceptación
- [ ] `POST /api/disciplinary/transcribe` devuelve shape de `contracts.json` J2.
- [ ] `pytest` verde. (Mockea Whisper en los tests para no depender del binario.)
