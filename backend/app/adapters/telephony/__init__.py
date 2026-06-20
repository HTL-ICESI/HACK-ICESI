"""
Adapter de telefonía (J1 — Captura de descargos por llamada). Dueño: David.

Port del patrón AFFIRMA (Due-Legal): un agente de voz ElevenLabs conduce la
diligencia de descargos por teléfono (Twilio), captura señales tipadas, y el
NÚCLEO DETERMINISTA (`domain/disciplinary/guardian.py`) decide si hay nulidad.

El agente NUNCA decide. Solo conduce el flujo del debido proceso y captura qué
pasó; el guardián evalúa el `DiligenceState` resultante.
"""
