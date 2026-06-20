# Proceso Disciplinario Laboral — Base de conocimiento para el sistema

> **Esta es la SPEC que implementa `guardian.py`.** Define cada etapa, su fundamento
> normativo, los documentos que produce y las **reglas de validación** verificables
> que determinan si el proceso es CONFORME, PARCIAL o NULO. Si cambia la norma,
> se ajusta este documento y el guardián en paralelo. (Dueño legal: David.)

## 0. Marco normativo aplicable (fuente de verdad)

| Norma | Qué regula | Uso en el sistema |
|---|---|---|
| Constitución Política, art. 29 | Debido proceso (actuaciones administrativas y disciplinarias) | Regla raíz: ninguna sanción sin proceso previo |
| CST, art. 115 (modificado por Ley 2466 de 2025, art. 7) | Procedimiento para imponer sanciones disciplinarias | Define las 7 garantías mínimas (ver §2) |
| CST, art. 114 | No se pueden imponer sanciones no previstas | Validación de tipicidad (ver §1) |
| CST, art. 113 | Límites a multas y suspensiones | Validación de proporcionalidad (ver §6) |
| Sentencia C-593 de 2014 (Corte Constitucional) | Constitucionaliza el debido proceso disciplinario | Estándar de garantías mínimas |
| Circular 0048 del 22 de mayo de 2026 (MinTrabajo) | Lineamientos operativos del debido proceso | Plazo de 5 días hábiles y doble instancia |

**Regla de vigencia:** estas referencias deben re-verificarse periódicamente (la
reforma es reciente y hay reglamentación en desarrollo). El sistema debe permitir
actualizar plazos y porcentajes sin tocar la lógica.

**Distinción crítica que el sistema debe aplicar primero:**
- Si la actuación es una **sanción disciplinaria** (llamado de atención,
  suspensión, multa) → aplica el procedimiento completo del art. 115 (las 7 etapas).
- Si la actuación es un **despido con justa causa** → por regla general NO es
  sanción disciplinaria y NO exige las formalidades plenas del art. 115; basta
  garantizar el derecho de defensa (ser oído). EXCEPCIÓN: si el reglamento interno
  o el contrato definen el despido como sanción, entonces sí aplica el art. 115
  completo.
- Campo de entrada requerido: `tipo_actuacion ∈ {sancion_disciplinaria, despido_justa_causa}`.

---

## 1. Pre-condición — Tipicidad (antes de la Etapa 1)

**Qué verifica:** que la conducta esté prevista como falta sancionable en el
reglamento interno, el contrato, la convención colectiva o la ley, ANTES de que
ocurriera (CST art. 114).

**Regla de validación:**
```
SI falta_tipificada == false ENTONCES proceso = NULO
  motivo: "Sanción no prevista previamente (art. 114 CST). El proceso es ineficaz desde el origen."
```

---

## 2. Las 7 garantías mínimas del art. 115 (checklist maestro)

El sistema evalúa el proceso contra estas 7 garantías. Cada una mapea a una o más
etapas y produce un booleano.

1. `comunicacion_apertura_formal` — comunicación formal y escrita de apertura.
2. `formulacion_cargos_concretos` — indicación clara de hechos, conductas u omisiones.
3. `traslado_pruebas` — entrega de las pruebas que sustentan los cargos.
4. `termino_defensa_minimo` — término no inferior a 5 días hábiles para la defensa.
5. `oportunidad_descargos` — el trabajador pudo manifestarse y controvertir pruebas.
6. `decision_motivada` — pronunciamiento definitivo motivado e identificando causas.
7. `derecho_impugnacion` — posibilidad de impugnar la decisión (doble instancia).

**Causales de nulidad (si cualquiera es false, la sanción es anulable):**
cualquiera de las 7 garantías ausente vicia el proceso. Las más graves (generan
nulidad directa, severidad ALTA): ausencia total de citación, ausencia de
descargos, término inferior a 5 días hábiles, cargos genéricos sin hechos concretos.

---

## 3. Etapa 1 — Investigación preliminar

- **Documento:** `acta_investigacion_preliminar`. **Fundamento:** art. 115 CST; inmediatez.
- **Campos:** `fecha_conocimiento_hechos`, `fecha_acta`, `lista_pruebas`,
  `norma_infringida`, `decision_apertura ∈ {abrir, archivar}`.

```
demora_dias = fecha_apertura - fecha_conocimiento_hechos
SI demora_dias > UMBRAL_INMEDIATEZ (config, p.ej. 30 días hábiles sin justificación)
  ENTONCES alerta = "Posible violación al principio de inmediatez (condonación de la falta)"
SI lista_pruebas vacía Y decision_apertura == abrir
  ENTONCES alerta = "Apertura sin sustento probatorio"
```

---

## 4. Etapa 2 — Citación a descargos (etapa más sensible)

- **Documento:** `citacion_descargos`. **Fundamento:** art. 115 CST + Circular 0048/2026 + art. 29 CN.
- **Campos:** `fecha_citacion`, `fecha_diligencia`, `cargos_texto`,
  `pruebas_trasladadas[]`, `derecho_acompanamiento_informado`, `hora_diligencia`, `lugar_diligencia`.

```
# REGLA CRÍTICA: término mínimo de 5 días hábiles entre citación y diligencia
dias_habiles = habiles_entre(fecha_citacion, fecha_diligencia)
SI dias_habiles < 5 ENTONCES garantia[4]=false; severidad=ALTA
  motivo: "Término de defensa inferior a 5 días hábiles (art. 115 CST mod. Ley 2466/2025, Circular 0048/2026)."

SI cargos_texto es genérico (sin hechos/fechas/norma) ENTONCES garantia[2]=false; severidad=ALTA
  ejemplos_prohibidos: ["falta de compromiso","mala actitud","bajo desempeño"] sin hechos concretos
  motivo: "Cargos imprecisos. El trabajador tiene derecho a saber exactamente qué conducta se le imputa."

SI pruebas_trasladadas vacío ENTONCES garantia[3]=false; severidad=ALTA
  motivo: "No se trasladaron las pruebas con la citación (se impide la contradicción)."

SI derecho_acompanamiento_informado == false ENTONCES garantía parcial; severidad=MEDIA
  nota: "Si el trabajador es sindicalizado, la omisión del derecho a 2 representantes sindicales es de mayor gravedad."
```

---

## 5. Etapa 3 — Diligencia de descargos

- **Documento:** `acta_descargos`. **Fundamento:** art. 115 CST.
- **Campos:** `trabajador_comparecio`, `version_trabajador`, `pruebas_aportadas[]`,
  `decision_acompanamiento`, `trabajador_firmo`, `testigos[]` (si no firmó), `silencio_voluntario`.

```
# Silencio NO es vicio: distinguir "no tuvo oportunidad" de "tuvo oportunidad y calló"
SI trabajador_comparecio==true Y silencio_voluntario==true
  ENTONCES garantia[5]=true   # ejerció su derecho legítimamente; NO es vicio
SI oportunidad_real_descargos==false (se le negó o interrumpió la palabra)
  ENTONCES garantia[5]=false; severidad=ALTA

SI trabajador_comparecio==false Y citacion_valida==true
  ENTONCES proceso_continúa=true; nota="Se entiende renuncia a pronunciarse; se decide con pruebas obrantes."

SI trabajador_firmo==false Y len(testigos)<2
  ENTONCES alerta="Acta sin firma del trabajador y sin 2 testigos que respalden la negativa."
```

---

## 6. Etapa 4 — Análisis y decisión motivada

- **Documento:** `decision_motivada`. **Fundamento:** art. 115 CST num. 5-6; art. 113 CST; in dubio pro disciplinado.
- **Campos:** `decision ∈ {archivar, sancionar}`, `motivacion_texto`, `tipo_sancion`,
  `dias_suspension`, `valor_multa`, `salario_dia`, `reincidencia`.

```
SI decision==sancionar Y motivacion_texto vacío/genérico
  ENTONCES garantia[6]=false; severidad=ALTA
  motivo: "Decisión no motivada; debe identificar hechos, pruebas y razones (art. 115 num. 5)."

# Proporcionalidad — suspensión (art. 113 CST)
SI tipo_sancion==suspension:
  SI reincidencia==false Y dias_suspension>8  -> "Suspensión excede 8 días (primera vez). Exceso ineficaz; obliga a pagar salarios."
  SI reincidencia==true  Y dias_suspension>60 -> "Suspensión excede 2 meses (reincidencia)."

# Proporcionalidad — multa (art. 113 CST)
SI tipo_sancion==multa:
  SI motivo_multa NO en {retraso, falta_al_trabajo} -> "Multa solo procede por retrasos o faltas al trabajo."
  SI valor_multa > (salario_dia / 5)               -> "Multa excede 1/5 del salario diario."

SI prueba_insuficiente==true Y decision==sancionar -> "Debió aplicarse in dubio pro disciplinado (archivar ante la duda)."
```

---

## 7. Etapa 5 — Derecho a impugnar (doble instancia)

- **Documento:** `resolucion_recurso` (si se interpone). **Fundamento:** Ley 2466/2025 + Circular 0048/2026.
- **Campos:** `recurso_informado_en_decision`, `superior_distinto`, `tipo_recurso`,
  `resolucion ∈ {confirmar, revocar, modificar}`.

```
SI recurso_informado_en_decision==false
  ENTONCES garantia[7]=false; severidad=ALTA
  motivo: "No se informó el derecho a impugnar (doble instancia, Ley 2466/2025)."
SI recurso_interpuesto==true Y superior_distinto==false
  ENTONCES alerta="El recurso lo resolvió la misma persona que sancionó (no hay segunda instancia real)."
```

---

## 8. Clasificación del proceso (salida del motor)

```
garantias_ok = suma(garantia[1..7] == true)

SI falta_tipificada == false                         -> NULO  (tipicidad incumplida)
SINO SI garantias_ok == 7                            -> CONFORME
SINO SI existe alguna garantía con severidad ALTA ausente
       (citación ausente, descargos ausentes, término < 5 días, cargos genéricos)  -> NULO
SINO SI 4 <= garantias_ok <= 6                       -> PARCIAL  (vicios subsanables)
SINO                                                  -> NULO
```

**Consecuencia jurídica que el sistema debe reportar:**
- CONFORME → la sanción/decisión es válida.
- PARCIAL → riesgo; documentar qué etapa rehacer antes de sancionar.
- NULO → la sanción es anulable. Si se trata de un despido apoyado en este proceso,
  puede convertirse en **despido injustificado** con indemnización (art. 64 CST),
  pago de salarios y eventual acción por vulneración de derechos fundamentales.

---

## 9. Excepción — Micro y pequeñas empresas

```
SI num_trabajadores <= 10 O empleador_servicio_domestico == true
  ENTONCES procedimiento_simplificado = true
  requisitos_minimos: [notificar hechos imputados, garantizar derecho de defensa,
                       escuchar al trabajador, sancionar proporcionalmente]
  nota: "No se exige el procedimiento completo (Circular 0048/2026); aplicar checklist reducido."
```

---

## 10. Orden de evaluación del motor

```
1. determinar tipo_actuacion (sancion vs despido_justa_causa)
2. validar tipicidad (§1)            -> si falla: NULO
3. validar inmediatez (§3)           -> alerta si demora excesiva
4. validar citación (§4)             -> garantías 1,2,3,4
5. validar diligencia (§5)           -> garantía 5
6. validar decisión (§6)             -> garantía 6 + proporcionalidad
7. validar impugnación (§7)          -> garantía 7
8. clasificar (§8)                   -> CONFORME / PARCIAL / NULO
```

**Formato de salida (por proceso):**
```json
{
  "tipo_actuacion": "sancion_disciplinaria",
  "clasificacion": "PARCIAL",
  "garantias_ok": 5,
  "garantias_total": 7,
  "vicios": [
    {"garantia": "termino_defensa_minimo", "severidad": "ALTA",
     "norma": "art. 115 CST (Ley 2466/2025), Circular 0048/2026",
     "detalle": "Solo 2 días hábiles entre citación y diligencia (mínimo 5)."}
  ],
  "consecuencia": "Sanción anulable; rehacer la citación respetando el término.",
  "recomendacion": "Reprogramar diligencia con >=5 días hábiles y reiniciar desde Etapa 2."
}
```
