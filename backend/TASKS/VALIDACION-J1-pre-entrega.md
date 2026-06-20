# Validación pre-entrega — J1 Pipeline Disciplinario

> Generado tras revisión exhaustiva de `feat/fixes` (commits 404ef99 · 81e3e57 · 63874d8).
> 332/332 tests pasan. Los puntos de abajo son lo que queda por resolver antes de mergear.

---

## SECCIÓN A — Bugs técnicos (arreglar antes de merge)

### A1. `close_process` registra el `from_state` incorrecto en el audit trail

**Archivo:** `app/services/pipeline_service.py` línea ~488

El método cambia `proc.state = ProcessState.CERRADO` **antes** de crear el audit entry,
y luego intenta recuperar el estado anterior leyendo `proc.audit_trail[-1].from_state`.
Eso da el `from_state` de la penúltima acción, no del cierre.

```python
# Como está (MAL):
proc.state = ProcessState.CERRADO          # ya cambió
proc.add_audit_entry(
    from_state=ProcessState(proc.audit_trail[-1].from_state) ...  # lee el audit anterior
)

# Fix (1 línea extra antes del cambio):
old_state = proc.state                     # capturar ANTES
proc.state = ProcessState.CERRADO
proc.add_audit_entry(from_state=old_state, ...)
```

Todos los demás métodos del service hacen `old_state = proc.state` correctamente.
Solo `close_process` se saltó el patrón.

---

### A2. `action` en AbsenceRequest es `str` con validación manual, no Literal

**Archivo:** `app/api/routers/disciplinary.py`

```python
class AbsenceRequest(BaseModel):
    action: str   # manual if req.action not in {...} después
```

El service ya tiene lógica sobre `"reschedule"` y `"proceed_in_absence"`.
Pydantic debería validarlo solo:

```python
from typing import Literal
class AbsenceRequest(BaseModel):
    action: Literal["reschedule", "proceed_in_absence"]
```

Elimina el `if req.action not in {...}` manual del endpoint. Mismo problema
(menos grave) con `falta_level` y `chosen_sanction` en `DecisionRequest` —
también son `str` con validación manual en vez de Literal.

---

### A3. `transition_back` no tiene endpoint en el router

**Archivo:** `app/api/routers/disciplinary.py`

`PipelineService.transition_back()` está implementada y tiene tests, pero no hay
`POST /{process_id}/transition-back` en el router. Sin ese endpoint, el frontend
no puede retroceder el proceso (ej. volver de `EN_REVISION` a `CITADO` para una
segunda ronda). Es la única operación del service sin exposición API.

Fix mínimo:

```python
class TransitionBackRequest(BaseModel):
    target_state: str
    reason: str

@router.post("/{process_id}/transition-back")
def transition_back(process_id: str, req: TransitionBackRequest, ...):
    try:
        proc = svc.transition_back(ctx, process_id,
                                   target_state=ProcessState(req.target_state),
                                   reason=req.reason)
    except (PipelineError, ValueError) as exc:
        _pipeline_error(PipelineError(str(exc)))
    return proc.to_dict()
```

---

## SECCIÓN B — Preguntas de comportamiento (confirmar con el abogado)

> Pegar estas preguntas directamente y devolver las respuestas para que las integre.

---

**B1. Comprobante de notificación: ¿cuándo debe subirse?**

El sistema bloquea `LISTO_PARA_CITAR → CITADO` si no hay comprobante (`notification_proof_id`).
El comprobante es una evidencia marcada con `is_notification_proof=True`.

Pregunta: ¿el comprobante se sube **antes** de llamar `/cite` (flujo actual),
o el abogado primero emite la citación y luego sube el comprobante como constancia de que se entregó?

Si es lo segundo, hay que separar `/cite` de `/confirm-delivery` — el bloqueo
actual asumiría que el comprobante existe antes de enviar la citación.

---

**B2. Segunda ronda: ¿quién la inicia y cómo?**

Para una segunda diligencia el flujo es:
1. Proceso en `DILIGENCIA_REALIZADA` o `EN_REVISION`
2. Abogado hace `transition_back` a `CITADO` con motivo
3. Nuevo `/cite` con nueva fecha (5 días hábiles otra vez)
4. Nuevo `/session`

¿Es ese el flujo esperado? ¿O la segunda ronda se registra desde
`DILIGENCIA_REALIZADA` directamente sin volver a `CITADO` (porque la citación de la primera ronda ya les avisó que habría ampliacón)?

Si no requiere nueva citación formal para la segunda ronda, hay que ajustar el state machine.

---

**B3. Transcripción: ¿va en el mismo llamado que la diligencia o después?**

`POST /{process_id}/session` acepta `transcript: str` en el mismo body.
En la práctica, Whisper tarda (proceso async). ¿El abogado espera a tener el
transcript antes de registrar la diligencia, o registra primero y adjunta el
transcript después cuando Whisper termina?

Si es lo segundo, necesitamos `PATCH /{process_id}/session/{session_id}/transcript`.

---

**B4. Subir evidencia en vacío satisface el checklist automáticamente**

Cuando se llama `/evidence`, el sistema auto-marca `checklist.at_least_one_proof = True`
sin importar el contenido del archivo. Un archivo en blanco (0 bytes) pasaría.

¿Está bien así para el demo? ¿O el abogado debería marcar manualmente ese ítem
una vez ha revisado el archivo?

---

**B5. Defaults del contrastador: G6 y G7 asumidos como cumplidos**

En `ContrastRequest`, `decision_motivada=True` y `derecho_impugnacion=True` son los
defaults. El guardián J3 asume que esas dos garantías se cumplieron aunque el abogado
no las marque explícitamente.

G6 (decisión motivada) y G7 (doble instancia/Ley 2466) son las garantías que la Ley 2466
añadió. ¿Deberían ser `False` por defecto (el abogado las confirma activamente) o `True`
(se asumen cumplidas porque el sistema las gestiona)?

---

**B6. `citation_date` la pone el abogado — ¿puede ser pasada?**

El endpoint `/cite` acepta cualquier `citation_date: date` sin validar que sea futura.
Si el abogado ingresa una fecha de hace 10 días, el sistema acepta la citación.

¿Hay que añadir validación `citation_date >= today`? ¿O hay casos legítimos donde
se registra una citación con fecha pasada (ej. proceso físico ya iniciado que se
está digitalizando)?

---

**B7. ¿El recurso puede terminar en "denegado" además de "resuelto/cerrado"?**

El estado `RECURSO → CERRADO` cubre el cierre del recurso. Pero la Ley 2466 prevé que
el recurso puede resolverse confirmando la decisión o revocándola.

¿El sistema necesita distinguir entre cierre por "recurso confirmado" vs "recurso revocado",
o ambos son simplemente `CERRADO` con texto libre en `reason`?

---

**B8. ¿El sistema debe impedir sancionar una falta leve con terminación?**

El motor recomienda la sanción máxima permitida por nivel:
- leve → solo llamado de atención
- grave → hasta suspensión
- gravísima → hasta terminación con justa causa

Actualmente, si el abogado llama `/decision` con `falta_level="leve"` y
`chosen_sanction="terminacion_justa_causa"`, el motor usa el `requested_sanction`
pero lo ignora si no está en el conjunto permitido (devuelve llamado de atención).

¿Debe el API devolver un error 422 si `chosen_sanction` no está permitida para
`falta_level`, o solo ajustar silenciosamente la recomendación y dejar al abogado
confirmar?

---

## SECCIÓN C — Lo que está bien y no necesita cambios

- Máquina de estados: 8 estados, transiciones deterministas, sin LLM. ✅
- Plazo de 5 días hábiles con bloqueo duro y override documentado. ✅
- `proceed_in_absence` bloqueado en primera inasistencia. ✅
- SHA-256 en servidor (el cliente no envía el hash). ✅
- `ActaSignatures.is_valid()` con escenario "negativa + 2 testigos". ✅
- Recurso: validación de perfil distinto al decisor original. ✅
- `DisciplinaryConfig` rechaza `min_notice_days < 5`. ✅
- Audit trail: `PipelineAuditEntry` es frozen dataclass → inmutable. ✅
- Sanciones bloqueadas con motivo (`_BLOCKED` dict explícito). ✅
- 332/332 tests pasan, incluyendo los 17 de `test_disciplinary_pipeline.py`. ✅
- Router registrado en `main.py`, service wired en `deps.py`. ✅

---

## Resumen para quien responde

| # | Tipo | Impacto si no se resuelve |
|---|------|--------------------------|
| A1 | Bug — audit trail de cierre incorrecto | Audit trail muestra estado incorrecto al cerrar |
| A2 | Mejora — Literal types en requests | Validación manual frágil, fácil de tipar mal |
| A3 | Gap — falta endpoint transition-back | Segunda ronda imposible desde el frontend |
| B1 | Pregunta flujo | Podría bloquear citación en el momento equivocado |
| B2 | Pregunta flujo | Segunda ronda puede no funcionar en demo |
| B3 | Pregunta flujo | Transcript puede quedar vacío en acta |
| B4 | Pregunta comportamiento | Bajo riesgo para demo |
| B5 | Pregunta legal (G6/G7) | Puede sub-detectar vicios de Ley 2466 |
| B6 | Pregunta validación | Riesgo de backdating en demo |
| B7 | Pregunta negocio | Recurso no distingue resultado |
| B8 | Pregunta legal | Puede permitir sanción desproporcional sin error explícito |
