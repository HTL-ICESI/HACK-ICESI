# Plan de Frontend — Cerebro Laboral HG (Reto 4 ICESI 2026)

> **Rama:** `feat/fe-app` · **Dueño:** Juanes · **Stack:** Next.js (App Router) + TypeScript + Tailwind + shadcn/ui
> **Fuente de verdad de datos:** [`icesi-playbook/contracts.json`](../../icesi-playbook/contracts.json) — las shapes están congeladas.
> Se construye contra **mocks** tipados; cuando el backend esté arriba, se cambia el flag `USE_MOCKS` y se apunta a `NEXT_PUBLIC_API_URL`. Las shapes NO cambian.

---

## Tesis de UI (framing de TODA la app)

No vendemos "ahorra tiempo con IA", vendemos **riesgo evitado**. El protagonista en pantalla es siempre *la plata en riesgo* y *la nulidad evitada*, nunca "la IA".

---

## Decisiones tomadas (Hora 0 del frontend)

| Tema | Decisión |
|---|---|
| **Design system** | Lo entrega el equipo como **tokens CSS** (variables). La Fase 0 monta una capa swappable: variables en `:root` que Tailwind consume vía `var()`. Hasta recibirlo, set neutro de placeholder. Reemplazar tokens = cero rework en componentes. |
| **Nombre / logo** | **Placeholder neutro** en un componente `<Brand/>` aislado. Cuando haya naming, es swap de un solo archivo. |
| **Money-shot (dashboard)** | El tratamiento visual lo define el design system del equipo, no el front por su cuenta. |
| **Ubicación** | `cerebro-laboral-hg/frontend` (al lado de `backend`). |

---

## Fases

| Fase | Entregable | Pantallas | Depende de |
|---|---|---|---|
| **0 — Cimientos** | Scaffold Next.js App Router + TS + Tailwind + shadcn. Capa de **tokens CSS swappable** (placeholder). `lib/types.ts` (de `shared_types`) + `lib/mocks.ts` (de los `response_example`) + `lib/api.ts` con flag `USE_MOCKS`. Primitivos transversales: `SourceChip`, `StatusBadge`, `Money`, `SeverityTag`, `<Brand/>`. | — | design system (tokens CSS) |
| **1 — Shell + Money-shot** | Nav + switch de persona + selector de empresa (F1) · Dashboard con número mágico animado (count-up) + 3 tarjetas + alertas (F3). | F1, F3 | Fase 0 |
| **2 — Compliance Vivo** | Stepper de 5 pasos: upload → extracción citada → riesgos → liquidación determinista → subsanación (estado `blocked` + botón Aprobar). | F2 | Fase 0 |
| **3 — Disciplinario Blindado (la joya)** | Diligencia → grabar (Web Audio API + fallback a transcript mock) → Guardián en vivo (checklist + banner de nulidad) → 3 documentos (`decision_final` bloqueada). | F4 | Fase 0 |
| **4 — RRHH (nice-to-have)** | Vista accionable sin jerga + plantilla gamificada de vacaciones. | F5 | Fase 1 |
| **5 — Pulido demo** | Count-up, transiciones con cubic-bezier, navegación instantánea entre las 3 vistas, `prefers-reduced-motion`, fallbacks por feature. | todas | Fases 1-3 |

**Ruta crítica para la demo:** Fase 0 → 1 → 2 → 3.
Una vez hecha la Fase 0, las fases 1/2/3 son independientes entre sí → se pueden construir en cualquier orden o en paralelo.

---

## Pantallas → endpoints (de contracts.json)

| ID | Pantalla | Persona | Endpoints |
|---|---|---|---|
| F1 | Shell + navegación | ambos | — |
| F3 | Dashboard (home) | ambos | `GET /api/dashboard/exposure` (M6) |
| F2 | Compliance Vivo | Abogado HG | M1 `POST /api/ingest` → M2 `POST /api/extract` → M3 `POST /api/compliance/analyze` → M4 `POST /api/liquidation/compute` → M5 `POST /api/remediation/generate` |
| F5 | Alertas / Equipo | RRHH | `GET /api/dashboard/exposure` (M6, campo `alerts`) |
| F4 | Disciplinario Blindado | Abogado HG | J2 `POST /api/disciplinary/transcribe` → J3 `POST /api/disciplinary/guardian` → J4 `POST /api/disciplinary/documents` |

---

## Contrato técnico (no negociable)

Reglas del backend que el front DEBE respetar visualmente:

1. **Trazabilidad determinística** — Ningún número/afirmación se muestra sin su `source` (span citado). Todo dato calculado es un chip clickeable (`<SourceChip>`) que abre la cita textual con `confidence`. Sin source → no se afirma.
2. **`status: "needs_human"`** — badge ámbar honesto ("requiere revisión humana"). NUNCA mostrar data inventada en ese caso.
3. **Determinista vs LLM** — números (liquidación, exposición) → badge verde "✓ calculado". Texto redactado por LLM (otrosí, actas) → "borrador · revisar".
4. **Estados bloqueados** — `validation.blocked: true` (M5) o `can_proceed: false` (J3) → el documento se muestra **bloqueado con el motivo**, no se puede aprobar. **Ese bloqueo ES la demostración de valor.**

---

## Los dos roles (persona switch)

- **Rol A — Abogado HG (experto):** ve todo el detalle (citas, spans, razonamiento). Valida y aprueba. Tono técnico, denso, con citas a la vista.
- **Rol B — RRHH (operador):** ve lo accionable ("qué hacer y cuándo"), sin jerga. Aquí vive el dashboard gamificado. **Evaluado por el jurado** ("¿es accionable para RRHH?").

---

## Qué SÍ / qué NO construir

- **SÍ (core de la demo):** F1 shell · F3 dashboard con número mágico · F2 flujo compliance completo · F4 diligencia con guardián en vivo.
- **Nice-to-have:** F5 plantilla gamificada · vista RRHH pulida · animación del número mágico subiendo.
- **NO (es visión, va solo en el deck):** llamada telefónica real · login real · versionado de documentos · panel admin del vigilante normativo · reclasificación masiva por lotes (en la app se muestra 1 contrato; el batch se narra).

---

## Recorrido de la demo (el front lo debe soportar fluido, sin recargas)

1. Abrir → **Dashboard**: "$71.175.000 COP en riesgo" (impacto inmediato).
2. **Compliance**: subir contrato → extracción citada → riesgos → liquidación calculada → genera el otrosí (la credibilidad).
3. **Disciplinario**: iniciar diligencia → grabar descargos → el guardián frena la nulidad en vivo → la decisión final queda bloqueada (el wow).
4. Cerrar → **Dashboard**: "1 nulidad evitada" (el cierre de riesgo).

---

## Datos mock

`lib/mocks.ts` contiene los `response_example` de `contracts.json` (shapes exactas del backend). Flag `USE_MOCKS=true`. Cuando el backend esté arriba: flag a `false` + `NEXT_PUBLIC_API_URL`.

---

## Estado

- [x] Rama `feat/fe-app` creada y pusheada.
- [x] Plan v2 aprobado y versionado.
- [ ] **Bloqueado esperando:** design system (tokens CSS) para arrancar Fase 0.
