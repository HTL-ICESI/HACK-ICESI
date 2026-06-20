# TAREA — M5: Generador de subsanación

> Lee primero: `AGENT-ONBOARDING.md`, `icesi-playbook/contracts.json` (bloque M5).
> Trabaja en `feat/m5-subsanacion`. Depende de M3 (gaps) y M4 (cifras).

## Qué hace M5
Dado un gap + las cifras del motor, genera el documento corrector: **otrosí**, **instrucción
a nómina**, **acta de terminación** o **contrato corregido**. El LLM REDACTA; el código
VALIDA que toda cifra del documento coincida con el motor.

## Regla de oro (la más importante de M5)
Ninguna cifra del documento legal sale del LLM. El service inyecta las cifras ya calculadas
por M4 y luego **verifica que aparezcan intactas en el texto**. Si no coinciden →
`BlockedOutput` (el documento NO se muestra). Ya hay stub en `app/services/remediation_service.py`.

## Dónde va el código
- Service → `app/services/remediation_service.py` (EXISTE, completar `_figures_match` de verdad).
- Adapter LLM → `app/adapters/llm/claude_client.py` (`draft_document`, completar).
- Router → `app/api/routers/remediation.py` → `POST /api/remediation/generate`. Registrar en `main.py`/`deps.py`.

## Tests obligatorios (`tests/services/test_remediation.py`)
1. Cifra del LLM coincide con M4 → documento OK, `blocked=False`.
2. Cifra alterada → `BlockedOutput` (mockeando el LLM para que devuelva una cifra distinta).
3. La validación de cifras es determinista.

## Criterios de aceptación
- [x] `_figures_match` / `validate_figures` verifica cada figura en el texto.
- [x] Documento con cifra divergente → bloqueado.
- [x] `POST /api/remediation/generate` devuelve shape de `contracts.json` M5.
- [x] `pytest` verde (205 passed, 1 skipped).

---

## Decisiones de diseño post-implementación

### ADR-M5-001 — Inyección de datos de partes desde el DocumentRecord
**Fecha:** 2026-06-18  
**Problema detectado:** El primer skeleton generado era genérico — sin nombre de empleador,
trabajador ni bloque de firmas. Un otrosí colombiano real requiere identificación de partes
y firmas para ser un instrumento legal válido.  
**Decisión:** `generate()` acepta `record: DocumentRecord | None`. Si se provee, el service
extrae `employer_name`, `employer_nit`, `worker_name`, `worker_doc`, `worker_role` y
`contract_start` vía `_extract_party_data()` y los pasa a `build_skeleton()` como
`party_data`. Los templates usan `_SafeDict` + `format_map` para que claves faltantes
muestren placeholders en lugar de lanzar `KeyError`.  
**Impacto:**
- `app/domain/remediation/templates.py` — skeletons enriquecidos con encabezado de partes y bloque de firmas.
- `app/services/remediation_service.py` — nueva firma `generate(..., record=None)`.
- `app/api/routers/remediation.py` — `RemediationRequest` agrega `record: DocumentRecord | None`.
- `tests/services/test_remediation.py` — test `test_skeleton_incluye_datos_de_partes` verifica que el body contenga empleador, trabajador, NIT y C.C. del gold case.  
**Por qué `record` es opcional:** para no romper integración con callers que no tengan el record disponible; en ese caso los campos muestran `[EMPLEADOR]`/`[TRABAJADOR]` como placeholder.

---

### ADR-M5-002 — `build_figures` filtra por claves del skeleton (bug: BlockedOutput falso en g4+M4)
**Fecha:** 2026-06-18  
**Problema detectado (bug):** `g4 + liquidation_data` lanzaba `BlockedOutput` incorrecto.
`build_figures` metía TODAS las claves numéricas de M4 (`cesantias`, `prima`, `total`, etc.)
en el dict `figures`. `validate_figures` buscaba esos valores en el body, pero el skeleton
de g4 no los mencionaba → ningún valor de M4 aparecía en el texto → blocked=True en falso.  
**Decisión:** `build_figures(gap_id, remedy_type, liquidation_data)` ahora acepta
`remedy_type` y filtra las claves de M4 a solo aquellas que aparecen como `{placeholder}`
en el skeleton correspondiente (`_referenced_keys`). Las cifras de M4 se formatean como
COP con puntos de miles (`_format_cop`: `1000000.0 → '1.000.000'`) antes de inyectarlas;
`validate_figures` busca la cadena formateada en el body.  
**Impacto:**
- `templates.py` — `build_figures` nueva firma; `_format_cop`, `_referenced_keys` nuevas.
  Skeleton `g4_acta_terminacion` enriquecido con tabla de montos M4.
- `remediation_service.py` — pasa `doc_type` como segundo arg a `build_figures`.
- `test_remediation.py` — nuevo test `test_g4_con_m4_no_lanza_blocked`.  
**Descubierto mediante:** test E2E con `LiquidationInput(monthly_salary=2_000_000, days_worked=180)` sobre contrato término fijo vencido.

---

### ADR-M5-003 — Guardia ante body vacío o None del LLM adapter
**Fecha:** 2026-06-18  
**Problema detectado:** Si el adapter LLM devolvía `None` (error interno no manejado) o `""`, `validate_figures` lanzaba `TypeError` («argument of type 'NoneType' is not iterable») en lugar de `BlockedOutput`. El caller no esperaba `TypeError` y el error se propagaría sin control hacia el router.  
**Decisión:** En `generate()`, antes de llamar a `validate_figures`, se verifica `isinstance(body, str) and body.strip()`. Si falla → `BlockedOutput` con mensaje claro. Maneja simultáneamente `None`, `""` y strings de solo espacios.  
**Impacto:**
- `app/services/remediation_service.py` — guardia antes del bloque `validate_figures`.  
**Por qué no en `validate_figures`:** esa función es pura y sus callers siempre deberían pasar un string; la guardia correcta es en la capa de orquestación que recibe la respuesta del LLM.

---

### ADR-M5-004 — Validación de gap_id y doc_type en el router (boundary guard)
**Fecha:** 2026-06-18  
**Problema detectado:** Con `gap_id='g99'` (desconocido) y passthrough LLM, el service producía un "documento genérico" con texto "hallazgo g99" — output semánticamente inválido pero sin crash ni BlockedOutput, porque `figures={}` siempre pasa `validate_figures`.  
**Decisión:** Agregar `@field_validator` en `RemediationRequest` para `gap` y `doc_type`. gap_id debe ser uno de {g1..g5}; doc_type debe ser uno de {otrosi, instruccion_nomina, acta_terminacion, contrato_corregido}. Inputs inválidos retornan HTTP 422 con mensaje claro antes de llegar al service.  
**Impacto:** `app/api/routers/remediation.py` — dos field_validators; `_VALID_GAP_IDS`, `_VALID_DOC_TYPES` como conjuntos de módulo.  
**Por qué en el router y no en el service:** El router es el boundary de entrada del sistema externo (principio hexagonal). El service recibe objetos ya validados — no debe repetir validación de inputs.
