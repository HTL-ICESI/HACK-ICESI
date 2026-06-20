# Cerebro Laboral HG · WorkLab

Compliance laboral automatizado y gestión de procesos disciplinarios para **Hurtado Gandini Abogados** (Reto 4 — Laboral & Compliance, Legal Hack ICESI 2026).

El sistema convierte el derecho laboral colombiano en una herramienta operativa: detecta riesgos en los contratos con su norma exacta, cuantifica la exposición económica en pesos y blinda los procesos disciplinarios contra la nulidad por debido proceso.

---

## Los dos pilares

### 1. Compliance Vivo
Sube los contratos (uno o un lote en ZIP) y el sistema:
- **Extrae** los datos duros con su fuente (salario, jornada, vínculo, fechas) — M1/M2.
- **Detecta riesgos** normativos con su cita verificada — M3:
  - Jornada > 42h (Ley 2101/2021 art. 2, que modifica el CST art. 161).
  - Reclasificación de prestación de servicios (presunción laboral, CST art. 24).
  - Vacaciones acumuladas > 1 año (CST art. 186).
  - Contrato a término fijo vencido sin renovación (CST art. 46).
  - Mora en seguridad social (Ley 100/1993 art. 22).
- **Liquida** las prestaciones de forma determinista — M4 (cesantías, intereses, prima, vacaciones, indemnización) y exporta el **Excel formato HG** + una hoja "Memoria de Cálculo" con las fórmulas paso a paso.
- **Genera la subsanación** (otrosí, instrucción de nómina, acta) — M5.
- **El número mágico** — M6: la exposición económica del lote en COP, calculada en vivo.

### 2. Disciplinario Blindado
Conduce el proceso disciplinario garantizando el debido proceso:
- **Citación a descargos** generada con la data real del trabajador y enviada por WhatsApp (PDF).
- **Llamada de descargos** (ElevenLabs + Twilio): el agente conduce la diligencia y captura la conversación completa; el sistema trae la transcripción al terminar.
- **Guardián del debido proceso** (determinista): vigila las garantías del art. 115 CST + art. 29 CN y **bloquea la decisión final** si hay riesgo de nulidad.
- **Acta de la diligencia** generada con los descargos y enviada por WhatsApp.
- **Decisión final** habilitada solo cuando el expediente está completo.

---

## Arquitectura

```
backend/    FastAPI · hexagonal · multitenant (aislamiento por tenant_id)
frontend/   Next.js (App Router) · TypeScript · Tailwind · shadcn/ui
```

### Principio anti-alucinación
> El código determinista posee las garantías; el LLM solo redacta lenguaje.

- **Detección de riesgos:** reglas deterministas (Python puro). El identificador de cada norma está fijado en la regla y se **resuelve contra un corpus verificado** (`backend/data/corpus/verified/`) con texto literal, vigencia y fuente oficial. Sin nodo en el corpus, no se afirma el gap.
- **Liquidación:** funciones puras del CST (`backend/app/domain/liquidation`). Mismo input → mismo output, auditable. Verificado contra casos gold reales (±$1).
- **Guardián disciplinario:** evaluación determinista de 7 garantías con poder de veto.
- **Subsanación / documentos:** las cifras, partes y citas las pone el código; el LLM solo redacta prosa, y un validador **bloquea** el documento si una cifra no coincide con el motor.

### Módulos
| | |
|---|---|
| M1 ingesta · M2 extracción con cita · M3 compliance | M4 liquidación · M5 subsanación · M6 exposición · M7 gateway |
| J1 pipeline disciplinario (llamada) | J2 transcripción · J3 guardián · J4 documentos |

---

## Cómo correrlo

### Backend
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # configurar claves (Infermatic/TotalGPT, ElevenLabs, Twilio) — opcionales
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
# .env.local: NEXT_PUBLIC_USE_MOCKS=false, BACKEND_URL=http://localhost:8000
npm run dev
```

### Credenciales demo
| Rol | Correo | Contraseña |
|---|---|---|
| Abogado (Firma) | `abogado@hurtadogandini.co` | `Demo2026!` |
| RRHH (Empresa) | `rrhh@empresacliente.co` | `Demo2026!` |

---

## Telefonía / WhatsApp (opcional)
La llamada de descargos y el envío de documentos por WhatsApp usan ElevenLabs Agents + Twilio. Sin credenciales, el sistema **degrada de forma honesta** (muestra el preview de lo que enviaría, nunca finge un envío). Para adjuntar PDFs por WhatsApp, el backend debe ser alcanzable públicamente (`BACKEND_HOST`), p.ej. con un túnel; en modo sandbox de Twilio, el número destino debe unirse primero.

---

*Reto 4 — Laboral & Compliance · Legal Hack ICESI 2026.*
