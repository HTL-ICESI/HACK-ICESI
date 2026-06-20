# TAREA — J4: Generar los 3 documentos disciplinarios · Dueño: David

> Lee primero: `AGENT-ONBOARDING.md`, `icesi-playbook/contracts.json` (bloque J4).
> Trabaja en `feat/joya-j4-documentos`. Depende de J3 (guardián).

## Qué hace J4
Genera los tres documentos del proceso disciplinario: **citación a descargos**, **acta de
descargos** y **decisión final**. El LLM redacta sobre plantillas validadas.

## Regla de oro (el veto)
La **decisión final NO se genera** si el guardián (J3) dice `can_proceed=False`. Ya está el
guard en `app/services/disciplinary_service.py::generate_documents` (lanza `BlockedOutput`).
Mantén ese bloqueo: es la demostración de valor.

## Dónde va el código
- Service → `app/services/disciplinary_service.py` (EXISTE, completar `generate_documents`).
- Adapter LLM → `app/adapters/llm/claude_client.py` (`draft_document`).
- Plantillas → `data/templates/` (NUEVO): citación, acta, decisión (David valida la estructura).
- Router → `app/api/routers/disciplinary.py` (añade `POST /api/disciplinary/documents`).

## Tests obligatorios
1. Con `can_proceed=True` → genera los 3 documentos.
2. Con `can_proceed=False` (falta un paso) → `BlockedOutput`, NO genera la decisión.

## Criterios de aceptación
- [ ] Los 3 documentos con la shape de `contracts.json` J4.
- [ ] La decisión final se bloquea si hay nulidad pendiente.
- [ ] `pytest` verde.
