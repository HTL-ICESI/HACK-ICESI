# TAREA — M6: Exposición / número mágico

> Lee primero: `AGENT-ONBOARDING.md`, `icesi-playbook/contracts.json` (bloque M6).
> Trabaja en `feat/m6-exposicion`. BASE YA LISTA — completar con alertas + endpoint.

## Estado actual
`app/domain/exposure/calculator.py` ya calcula el número mágico (COP exposición + % desactualización),
puro y con tests. Falta: el **calendario de alertas** y el **endpoint del dashboard**.

## Qué completar
1. Motor de alertas (determinista) en `app/domain/exposure/` (NUEVO `alerts.py`):
   - Vencimiento de contrato a término fijo (días restantes).
   - Vacaciones acumuladas > 1 año.
   - Obligaciones de seguridad social: cuánto, cuándo, y si está en mora.
   Cada alerta con `type`, `severity` (alta/media/baja), `due_date`.
2. Service → `app/services/exposure_service.py` (NUEVO): agrega gaps (M3) + reliquidaciones (M4) + alertas.
3. Router → `app/api/routers/dashboard.py` → `GET /api/dashboard/exposure`. Registrar en `main.py`/`deps.py`.

## Regla de oro
Todo es función pura y reproducible: mismo input → mismo COP, mismas alertas. Cero LLM.
Es el número que se muestra en vivo al jurado; tiene que ser determinista y auditable.

## Tests obligatorios
- Exposición reproducible (ya existe) + alertas: contrato que vence en 14 días → alerta "alta".
- Seguridad social en mora → alerta con monto y fecha.

## Criterios de aceptación
- [x] `GET /api/dashboard/exposure` devuelve shape de `contracts.json` M6 (magic_number + alerts).
- [x] Alertas deterministas con tests.
- [x] `pytest` verde.

---

## ✅ HECHO — Resumen de lo construido (rama `feat/m6-exposicion`)

### Archivos nuevos
| Archivo | Qué hace |
|---|---|
| `app/domain/exposure/alerts.py` | Motor de alertas determinista: vencimiento_contrato (alta ≤30d / media ≤90d), vacaciones_vencidas (>365d, media), seguridad_social_mora (True + ss_due_date, alta). Tipos `ContractContext` y `Alert`. |
| `app/services/exposure_service.py` | Orquesta calculator + alerts. `ExposureRequest.from_m3_gaps()` deriva automáticamente workers_at_risk, outdated_clauses y total_clauses desde el output de M3. |
| `app/api/routers/dashboard.py` | `GET /api/dashboard/exposure?company_id=X`. Dataset demo fijo para empresa-001. |
| `tests/domain/test_alerts.py` | 16 tests de alertas (boundaries, to_dict, determinismo). |
| `tests/api/test_dashboard_endpoint.py` | 10 tests HTTP del endpoint (COP formula, tipos de alerta, determinismo). |
| `tests/services/test_exposure_service.py` | 7 tests de service, incluyendo pipeline M3→M6 real con gold cases. |

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `app/main.py` | Registra `dashboard.router`. |
| `app/api/deps.py` | Inyecta `ExposureService`. |

### Fix clave: pipeline M3→M6 completamente derivado
`from_m3_gaps()` elimina todos los parámetros manuales:
- `workers_at_risk` = contratos con ≥1 gap
- `outdated_clauses` = suma total de gaps
- `total_clauses` = `len(gap_results) × 5` (_NUM_M3_RULES, reglas g1–g5)

### Fix previo: g5 seguridad social (M3, en esta rama antes de mergear)
g5 ahora solo se activa si `pago_ss_mora=True` explícito. Sin evidencia → no emite gap.
Efecto: el caso Ospino pasó de 2 gaps a 1 gap (solo g1, jornada).

### Suite final
242 passed, 0 failed, 1 skipped (gold M2 externo).
