# TAREA — M3: Reglas de gaps + corpus normativo

> Lee primero: `AGENT-ONBOARDING.md`, `icesi-playbook/contracts.json` (bloque M3),
> `cerebro-laboral-hg/backend/README.md`. Trabaja en `feat/m3-compliance`.

## Qué hace M3
Cruza un `DocumentRecord` (salida de M2) contra el corpus normativo vigente y devuelve
los **gaps** (ausencias normativas) con su cita. Incluye la regla de **reclasificación
(Ley 2466/2025)** — criterio CALIFICADO por el jurado.

## Regla de oro
La etiqueta de gap la decide **código determinista** (reglas), NO el LLM. Cada gap trae su
`Citation` resuelta a un nodo real del corpus. Sin nodo en el corpus → no se afirma el gap.

## Dónde va el código
- Reglas deterministas → `app/domain/compliance/gap_rules.py` (YA EXISTE con 2 reglas semilla; amplíalo).
- Carga/resolución del corpus → `app/adapters/corpus/source_pack.py` (YA EXISTE) + `data/corpus/source_pack.json`.
- Service → `app/services/compliance_service.py` (NUEVO): orquesta record → gaps → resolver citas.
- Router → `app/api/routers/compliance.py` → `POST /api/compliance/analyze`. Registrar en `main.py` y `deps.py`.

## Reglas a implementar (mínimo)
1. Jornada > 42h (Ley 2101/2021) → ya está, mantener.
2. Reclasificación: `prestacion_servicios` con indicios → ya está, enriquecer con los 4 indicios.
3. NUEVAS: vacaciones acumuladas > 1 año · vencimiento de contrato a término fijo ·
   obligaciones de seguridad social (con fecha de causación). Validar umbrales con David.

## Tests obligatorios (`tests/domain/test_gap_rules.py`)
1. Jornada 48h → gap "alta" con cita Ley 2101.
2. `prestacion_servicios` → gap de reclasificación con cita Ley 2466.
3. Contrato conforme (42h, indefinido) → cero gaps.
4. Determinismo: mismo record → mismos gaps.

## Criterios de aceptación
- [ ] `pytest` verde con los tests nuevos.
- [ ] Todo gap tiene `Citation` que resuelve en `source_pack.json`.
- [ ] `app/domain/compliance/` no llama LLM ni I/O.
- [ ] `POST /api/compliance/analyze` devuelve la shape de `contracts.json` M3.
