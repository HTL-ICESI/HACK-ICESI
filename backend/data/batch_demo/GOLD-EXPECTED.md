# Lote GOLD — Resultados verificados (Cerebro Laboral HG)

> **Para testear el dashboard de Compliance en lote (`/batch`).** Sube este ZIP y
> compara lo que muestra la UI contra los valores de abajo. Todo es **determinista**:
> los gaps salen del motor de reglas (no del LLM) y la liquidación del motor M4, así
> que estos resultados se reproducen **idénticos** en cada corrida (offline o con LLM).

**Reproducción exacta:** backend en `:8000`, subir el ZIP a `POST /api/batch/ingest`,
o arrastrarlo en `/batch`. Valores capturados el 2026-06-19 con el motor determinista.

---

## Resumen del lote (5 contratos)

| Contrato | Trabajador | Vínculo | Riesgo | Gaps detectados | Exposición (COP) |
|---|---|---|---|---|---|
| `contrato_maria_restrepo.txt` | María Camila Restrepo | Término fijo | 🔴 **alto** | **g4** | $6.550.000 |
| `contrato_juan_ospino.txt` | Juan David Ospino | Indefinido | 🔴 **alto** | **g1, g3** | $8.384.146 |
| `contrato_ana_prestacion.txt` | Ana María Quintero | Prestación servicios | 🔴 **alto** | **g1, g2, g3** | $5.902.712 |
| `contrato_pedro_largo.txt` | Pedro Antonio Gaviria | Término fijo | 🔴 **alto** | **g3, g4** | $3.930.000 |
| `contrato_lucia_limpia.txt` | Lucía Fernanda Moreno | Indefinido | 🟢 **bajo** | _(ninguno)_ | $6.578.400 |

**Agregado esperado en el header:** 5 analizados · **4 en riesgo alto** · exposición total **$31.345.258**.

> El contrato de Lucía **no tiene gaps a propósito**: demuestra que el sistema no
> inventa riesgos (no es un detector de falsos positivos).

---

## Detalle verificado por contrato

### 1. María Camila Restrepo López — 🔴 alto (risk_score 3)
- C.C. 1.094.918.233 · Asesora de Compliance · término fijo · salario $2.500.000 · jornada 42h · vigencia 1 mar 2024 → 28 feb 2025
- **g4 (alta)** — Contrato a término fijo **VENCIDO hace 476 días** (CST art. 46)
- Liquidación M4: cesantías $2.500.000 · prima $2.500.000 · vacaciones $1.250.000 · indemnización $0 · **total $6.550.000**
- _(Nota: su contrato menciona 48h y luego "ajustar a 42h"; el extractor toma 42h → no dispara g1. Comportamiento determinista.)_

### 2. Juan David Ospino Martínez — 🔴 alto (risk_score 5)
- C.C. 1.042.440.655 · Auxiliar Administrativo · indefinido · salario $1.600.000 · jornada **48h** · inicio 14 ene 2023
- **g1 (alta)** — Jornada de **48h excede el máximo legal de 42h** (Ley 2101/2021)
- **g3 (media)** — Período laboral > 1 año sin evidencia de vacaciones (CST art. 186)
- Liquidación M4: cesantías $1.600.000 · prima $1.600.000 · vacaciones $800.000 · indemnización $4.192.146 · **total $8.384.146**

### 3. Ana María Quintero Salazar — 🔴 alto (risk_score 7)
- C.C. 1.144.205.870 · Recepcionista · **prestación de servicios** · pago $1.300.000 · jornada **44h** · inicio 1 feb 2024
- **g1 (alta)** — Jornada de **44h excede el máximo legal de 42h** (Ley 2101/2021)
- **g2 (media)** — Prestación de servicios con indicios de subordinación → **riesgo de reclasificación** (Ley 2466/2025)
- **g3 (media)** — Período laboral > 1 año sin evidencia de vacaciones (CST art. 186)
- Liquidación M4: cesantías $1.300.000 · prima $1.300.000 · vacaciones $650.000 · indemnización $2.496.712 · **total $5.902.712**

### 4. Pedro Antonio Gaviria Rojas — 🔴 alto (risk_score 5)
- C.C. 16.789.012 · Mensajero · término fijo · salario $1.500.000 · jornada 42h · vigencia 1 jun 2022 → 31 may 2024
- **g3 (media)** — Período laboral > 1 año sin evidencia de vacaciones (CST art. 186)
- **g4 (alta)** — Contrato a término fijo **VENCIDO hace 749 días** (CST art. 46)
- Liquidación M4: cesantías $1.500.000 · prima $1.500.000 · vacaciones $750.000 · indemnización $0 · **total $3.930.000**

### 5. Lucía Fernanda Moreno Castaño — 🟢 bajo (risk_score 0)
- C.C. 1.130.622.418 · Abogada Junior · indefinido · salario $3.000.000 · jornada **42h** · inicio 2 ene 2026
- **Sin gaps** — contrato conforme (jornada legal, vínculo correcto, vigente)
- Liquidación M4 (si se terminara sin justa causa): **total $6.578.400**

---

## Notas metodológicas (importante para el demo)

1. **Gaps = 100% deterministas.** Salen del motor de reglas sobre los campos extraídos
   por regex (jornada, vínculo, fechas). El LLM **no** decide ningún gap. Por eso este
   gold es reproducible al 100%, incluso con el LLM apagado.

2. **La "Exposición" es la liquidación M4 si el contrato se terminara *sin justa causa*
   hoy**, con parámetros operativos por defecto (días tope 360, antigüedad derivada de
   las fechas del contrato). Es una **estimación determinista del contrato**, no la cifra
   atada a nómina real.

3. **Gold atado al Excel real de HG (otro flujo):** la liquidación exacta de José Ospino
   del Excel (**$1.720.590,94**) se reproduce en el flujo de **un solo contrato con datos
   de nómina** (`scripts/e2e_gold.py`), no en el batch (que es contrato-solo). El batch
   prioriza el barrido masivo de *cumplimiento*, no la liquidación atada a nómina.
