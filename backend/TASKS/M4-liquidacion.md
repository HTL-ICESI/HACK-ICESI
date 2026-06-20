# TAREA — M4: Motor de liquidación (con CASO GOLD real)

> Lee primero: `AGENT-ONBOARDING.md`, `icesi-playbook/contracts.json` (bloque M4).
> Trabaja en `feat/m4-liquidacion`. BASE YA LISTA — esto es completar con las fórmulas REALES.

## 🥇 Caso gold (de un formato real de Hurtado Gandini)
Fuente: `icesi-playbook/Liquidación Formato.xlsx`, hoja **"JOSÉ OSPINO"**. Es una
liquidación real resuelta. **Úsala como el test exacto de M4** (reemplaza el `@pytest.mark.skip`).

```
Trabajador: JOSÉ ANDRÉS OSPINO — término indefinido — MOTIVO: Renuncia
Salario básico ................ 1.750.905
Promedio HE+recargos+comisiones .. 676.785   (salario variable -> promedio último año)
Auxilio de transporte ......... 249.095
SALARIO BASE LIQUIDACIÓN ...... 2.676.785   (= básico + promedio + auxilio)
Periodo liquidado ............. 66 días (01 ene – 06 mar 2026)

CESANTÍAS      = 2.676.785 × 66/360            = 490.743,85
INT. CESANTÍAS = 490.744 × 66 × 0.12/360       =  10.796,36
PRIMA          = 2.676.785 × 66/360            = 490.743,85
VACACIONES     = 2.427.690/30 × 9              = 728.306,88
                 (base SIN auxilio = 1.750.905 + 676.785; 9 días pendientes)
─────────────────────────────────────────────
TOTAL LIQUIDACIÓN .............................. 1.720.590,94   ← el test debe dar esto
```

## Reglas que el gold case enseña (¡importantes!)
1. **La base de liquidación se COMPONE:** `salario_básico + promedio_variable + auxilio_transporte`.
   El motor actual usa solo `monthly_salary` — hay que componerla.
2. **Vacaciones EXCLUYE el auxilio de transporte** (base = básico + promedio, sin auxilio) y
   depende de **días pendientes** (no del periodo trabajado): `base_sin_aux/30 × días_pendientes`.
   *(Variante de acumulación: `salario × días_trabajados/720` — ver 2ª hoja del Excel.)*
3. **Salario variable → promedio del último año** de HE+recargos+comisiones. Requiere el
   histórico de nómina (tabla `novedad_nomina`), NO solo el contrato.

## Motivo de terminación → qué se calcula
| Motivo | Cálculo |
|---|---|
| Renuncia | solo prestaciones |
| Justa causa | solo prestaciones |
| **Sin justa causa** | prestaciones **+ indemnización** (art. 64 CST) |
| Mutuo acuerdo | prestaciones |
| **Transacción** | prestaciones **+ bonificación acordada** |

## Bonificaciones (caso avanzado)
- Campo `bonificacion` + flag **salarial / no_salarial**.
- Una bonificación de mera liberalidad NO genera prestaciones, pero puede generar base de
  cotización de seguridad social según la **regla 60-40** (el no-salarial no puede superar el
  40% del total). Implementar como validación; calcular salud/pensión/fondo solidaridad si aplica.

## Campos de BD que esto requiere (ya añadidos en `feat/database`)
- `contrato.auxilio_transporte`, `contrato.salario_variable`, `contrato.fecha_retiro`
- `liquidacion.motivo_terminacion`, `liquidacion.bonificacion`
- promedios de variable → de `novedad_nomina` (tabla futura; para el gold case se pasan directos).

## Qué completar en el dominio
- `app/domain/liquidation/engine.py`:
  - `salario_base_liquidacion(basico, promedio_variable, auxilio)` (nueva, pura).
  - `vacaciones` → usar base SIN auxilio + días pendientes.
  - `indemnizacion(inp)` → término fijo (salarios faltantes) e indefinido (tabla art. 64).
  - `liquidate(...)` → sumar todo en `total` según el motivo de terminación.
- Constantes en `constants.py` validadas con el Excel.

## Tests obligatorios
1. **`test_caso_gold_jose_ospino`** → total = 1.720.590,94 (±$1 por redondeo).
2. Sin justa causa → incluye indemnización.
3. Vacaciones excluye auxilio de transporte.
4. Determinismo (mismo input → mismo output).

## Refinamientos de la entrevista (reglas precisas — no perder)
1. **Vacaciones acumuladas:** si la persona tiene varios PERÍODOS acumulados pendientes, al
   salir se pagan TODOS completos (no la proporción). Necesita: períodos acumulados, días
   pendientes, última fecha de disfrute. La fórmula proporcional (`días/720`) solo aplica
   cuando NO hay acumulados (caso "planito" del Excel José Ospino, que estuvo pocos meses).
2. **Auxilio de transporte:** aplica SOLO si salario ≤ 2 SMMLV. Condicional en el motor.
3. **Bonificación 60-40 (AVANZADO — caso raro, opcional):** base de cotización de seguridad
   social = `max(salario_real, 0.60 × total_entregado)`. Si el 60% del total queda por debajo
   del salario real → cotizar sobre el salario real. Descuentos al empleado: salud 4%,
   pensión 4%, fondo de solidaridad. Solo en terminación por transacción con bonificación.
4. **"Costo real para la empresa" (FEATURE OPCIONAL, no liquidación):** la hoja GASTO PERSONAL
   de `icesi-playbook/FORMATO NÓMINA.xlsx` calcula el costo patronal: salario + pensión patronal
   12% + ARL + CCF 4% + (SENA 2% + ICBF 3% solo si NO exonerado: trabajador >10 SMMLV o empresa
   no declarante) + provisión de prestaciones. Una persona de $2.5M cuesta ~$3.7M. Determinista.

> Prioridad: primero el CASO GOLD core (José Ospino). Los puntos 3 y 4 son opcionales/después.

## Regla de oro
`app/domain/liquidation/` es PURO y determinista. Cero LLM, cero I/O. Es lo que el jurado
audita como confiabilidad — y ahora coincide con un formato REAL de la firma.

## Criterios de aceptación
- [ ] `test_caso_gold_jose_ospino` ACTIVO y verde.
- [ ] Base compuesta (básico + promedio + auxilio); vacaciones sin auxilio.
- [ ] Indemnización por motivo de terminación.
- [ ] `pytest` 100% verde.
