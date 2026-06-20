# TAREA — J3: Guardián de debido proceso (LA JOYA) · Dueño: David

> Lee primero: `AGENT-ONBOARDING.md`, `icesi-playbook/contracts.json` (bloque J3).
> Trabaja en `feat/joya-j3-guardian`. BASE YA LISTA — validar y enriquecer el checklist.

## Estado actual
`app/domain/disciplinary/guardian.py` ya implementa el checklist determinista (5 pasos) con
tests. Si falta un paso → `nullity_alert=True` + `can_proceed=False` (bloquea la decisión).

## Qué validar/completar (trabajo legal de David)
1. **Confirmar los pasos del debido proceso** contra art. 29 CN + art. 115 CST + Código
   Procesal del Trabajo. ¿Faltan pasos? ¿El orden importa? ¿Hay términos específicos?
2. Para cada paso, afinar la `consequence` (qué nulidad concreta genera).
3. Añadir cita verificable (radicado CSJ Sala Laboral, ej. SL1706-2024) a cada paso.

## Regla de oro
`app/domain/disciplinary/guardian.py` es PURO y determinista. Es la joya: el jurado verá
que el sistema **bloquea la nulidad antes de que ocurra**. Cero LLM aquí.

## Tests (`tests/domain/test_guardian.py` — ya existen, amplía)
- Cada paso faltante dispara su nulidad con la cita correcta.
- Diligencia completa → puede proceder.
- Determinismo.

## Criterios de aceptación
- [ ] Checklist validado por David contra la norma (no inventado).
- [ ] Cada `MissingStep` con cita verificable.
- [ ] `pytest` verde.
