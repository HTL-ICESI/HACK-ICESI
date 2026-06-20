# TAREA: Dashboard de Batch Processing — Cerebro Laboral HG

> **Rama nueva:** `feat/batch-dashboard`  
> **Depende de:** `integracion-back-front` (mergeado o como base)  
> **Dueño:** Sara  
> **Prioridad:** Alta — es el caso de uso real (empresas 50+ empleados)

---

## Contexto del problema

El flujo actual (`/compliance`) es un **wizard de un solo contrato** con botones
manuales ("Detectar riesgos →", "Verificar liquidación →", etc.). Eso no escala
para un bufete que maneja 50–500 contratos. El abogado necesita cargar todo de
una vez, ver el progreso en vivo, y navegar un dashboard — no hacer clic 5 veces
por cada empleado.

**Caso de uso real:** Un cliente llega con 80 empleados. El abogado sube un ZIP
con los 80 contratos, el sistema los procesa en paralelo, y 2 minutos después
tiene un dashboard con semáforos de riesgo, filtros, y acceso al acta de
terminación de cada uno.

---

## Stack existente (no cambiar)

- **Backend:** FastAPI + Python 3.11, `.venv` en `cerebro-laboral-hg/backend/`
- **Frontend:** Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui
- **Auth:** Bearer token `demo-hg-key` en todos los endpoints
- **Proxy:** Next.js `rewrites()` en `next.config.ts` → `/api/*` → `http://localhost:8000/api/*`
- **LLM:** Anthropic Claude Haiku (M2 campos blandos, M5 redacción) con fallback a Infermatic
- **Módulos backend ya implementados:** M1 (ingest), M2 (extract), M3 (compliance), M4 (liquidation), M5 (remediation), M6 (exposure/dashboard)

---

## Lo que hay que construir

### 1. Backend — Batch endpoint

**Nuevo archivo:** `app/api/routers/batch.py`

```
POST /api/batch/ingest
  Body: multipart/form-data con campo "files" (múltiples archivos) O "zip" (un ZIP)
  Response: { batch_id: str, total: int, files: [str] }

GET /api/batch/status/{batch_id}
  Response: {
    batch_id: str,
    total: int,
    completed: int,
    results: [
      {
        doc_id: str,
        filename: str,
        status: "pending" | "processing" | "done" | "error",
        error?: str,
        summary?: {           ← cuando status=done, resumen rápido para la card
          worker_name: str,
          employer_name: str,
          risk_level: "alto" | "medio" | "bajo",
          risk_score: int,
          total_exposure: float,
          gaps: [{ gap_id, issue, severity, remedy_type }],
          gap_count: int
        }
      }
    ]
  }

GET /api/batch/result/{batch_id}/{doc_id}
  Response: resultado completo de ese contrato:
  {
    doc_id: str,
    filename: str,
    extract: ExtractResponse,       ← M2
    compliance: ComplianceResponse, ← M3
    liquidation: LiquidationResponse, ← M4
    remediation: RemediationResponse  ← M5 (gap[0])
  }
```

**Cómo implementar el processing:**

```python
# app/services/batch_service.py
import asyncio, uuid, zipfile, io
from typing import Dict

# Estado en memoria (para el demo; en producción sería Redis/DB)
_batches: Dict[str, dict] = {}

async def create_batch(files: list[tuple[str, bytes]]) -> str:
    batch_id = str(uuid.uuid4())[:8]
    _batches[batch_id] = {
        "total": len(files),
        "completed": 0,
        "results": {filename: {"status": "pending", ...} for filename, _ in files}
    }
    # Lanzar procesamiento en background (asyncio.create_task)
    asyncio.create_task(_process_batch(batch_id, files))
    return batch_id

async def _process_batch(batch_id, files):
    # Procesar cada contrato: M1 → M2 → M3 → M4 → M5
    # Actualizar _batches[batch_id] en cada paso
    # Manejo de errores: si M1 falla, marcar status="error" y continuar con el siguiente
    ...
```

**Descomprimir ZIP en el router:**
```python
if zip_file:
    zf = zipfile.ZipFile(io.BytesIO(await zip_file.read()))
    files = [(name, zf.read(name)) for name in zf.namelist()
             if not name.startswith("__MACOSX") and name.endswith((".txt", ".pdf", ".docx"))]
```

**Para M4:** usar los datos del CASE por defecto (días trabajados, causa de terminación)
de un objeto configurable. En el demo, usar valores hardcodeados razonables.
En producción, el abogado llenaría un formulario previo con los datos operativos de nómina.

---

### 2. Frontend — Nueva página `/batch`

**Estructura de archivos a crear:**

```
app/(app)/batch/
  page.tsx                          ← página principal del batch dashboard

components/batch/
  BatchDropzone.tsx                 ← dropzone que acepta ZIP o múltiples archivos
  BatchProgress.tsx                 ← lista de archivos con spinners / checks
  ContractCard.tsx                  ← card de un empleado (nombre, riesgo, exposición)
  ContractModal.tsx                 ← modal/slide-out con análisis completo
  BatchDashboardHeader.tsx          ← métricas resumen (total, en riesgo, exposición)
  BatchFilters.tsx                  ← filtros: severidad, riesgo, búsqueda por nombre
```

**Flujo de UX:**

```
1. BatchDropzone
   ├── Acepta .zip (recomendado) o múltiples .txt/.pdf/.docx con Ctrl+click
   ├── Al soltar → POST /api/batch/ingest → recibe batch_id
   └── Pasa a vista de progreso

2. BatchProgress (mientras polling)
   ├── Lista de archivos: [spinner] contrato_maria.txt  ← procesando
   │                      [✅]      contrato_juan.txt   ← listo
   │                      [❌]      contrato_roto.pdf   ← error
   ├── Poll GET /api/batch/status/{batch_id} cada 2 segundos
   ├── Cuando un archivo pasa a "done" → aparece la ContractCard en el grid
   └── Progress bar: "47 / 80 contratos procesados"

3. Dashboard (cuando completed > 0, mostrar mientras sigue procesando)
   ├── Header: [ 80 contratos | 23 en riesgo alto | $71M exposición total ]
   ├── Filtros: [🔍 buscar empleado] [Riesgo: Alto/Medio/Bajo] [Gap: g1/g2/g3/g4/g5]
   └── Grid de ContractCards

4. ContractCard
   ┌─────────────────────────────────┐
   │ 🔴 RIESGO ALTO                  │
   │ MARIA CAMILA RESTREPO           │
   │ Asesora de Compliance           │
   │ HURTADO GANDINI & ASOC.         │
   │                                 │
   │ g4 · Término fijo vencido       │
   │ Exposición: $2.130.669          │
   │                      [Ver →]    │
   └─────────────────────────────────┘

5. ContractModal (al clickear "Ver →")
   ├── Tabs: Datos extraídos | Riesgos | Liquidación | Subsanación
   └── Reutilizar ExtractedRecord, GapsList, LiquidationTable, RemediationPanel
       ya existentes — solo envolverlos en un modal con tabs
```

**Polling en el frontend:**
```typescript
// hooks/useBatchStatus.ts
export function useBatchStatus(batchId: string | null) {
  const [status, setStatus] = useState<BatchStatus | null>(null);

  useEffect(() => {
    if (!batchId) return;
    const interval = setInterval(async () => {
      const s = await getBatchStatus(batchId);
      setStatus(s);
      if (s.completed === s.total) clearInterval(interval); // terminar polling
    }, 2000);
    return () => clearInterval(interval);
  }, [batchId]);

  return status;
}
```

**Nuevas funciones en `lib/api.ts`:**
```typescript
export async function batchIngest(files: File[]): Promise<BatchIngestResponse>
export async function getBatchStatus(batchId: string): Promise<BatchStatusResponse>
export async function getBatchResult(batchId: string, docId: string): Promise<BatchResult>
```

---

### 3. Tipos TypeScript a agregar en `lib/types.ts`

```typescript
export type BatchItemStatus = "pending" | "processing" | "done" | "error";

export interface BatchItemSummary {
  worker_name: string;
  employer_name: string;
  risk_level: "alto" | "medio" | "bajo";
  risk_score: number;
  total_exposure: number;
  gap_count: number;
  gaps: Pick<Gap, "gap_id" | "issue" | "severity" | "remedy_type">[];
}

export interface BatchItem {
  doc_id: string;
  filename: string;
  status: BatchItemStatus;
  error?: string;
  summary?: BatchItemSummary;
}

export interface BatchIngestResponse {
  batch_id: string;
  total: int;
  files: string[];
}

export interface BatchStatusResponse {
  batch_id: string;
  total: number;
  completed: number;
  results: BatchItem[];
}

export interface BatchResult {
  doc_id: string;
  filename: string;
  extract: ExtractResponse;
  compliance: ComplianceResponse;
  liquidation: LiquidationResponse;
  remediation: RemediationResponse;
}
```

---

## Archivos de contratos demo para el ZIP

Para demostrar con datos reales, crear al menos **5 contratos de ejemplo** en
`backend/data/batch_demo/`:

```
contrato_maria_restrepo.txt     ← el existente (g4: término fijo vencido)
contrato_juan_ospino.txt        ← indefinido, jornada 48h (g1: jornada excesiva)
contrato_ana_prestacion.txt     ← prestación de servicios disfrazada (g2: reclasif.)
contrato_pedro_vacaciones.txt   ← vacaciones vencidas (g3)
contrato_lucia_mora_ss.txt      ← mora en seguridad social (g5)
```

Cada uno debe activar un gap diferente para que el dashboard muestre variedad.

---

## Correcciones cosméticas pendientes (de la sesión anterior)

Estas son pequeñas pero hacen diferencia en el demo:

1. **Fecha ISO en acta M5** — `CONTRATO DEL: 2024-03-01` debe ser `1 de mar de 2024`
   - Archivo: `backend/app/domain/remediation/templates.py`
   - La función `_party_defaults()` ya extrae `contract_start`. Pasarla por un
     formateador de fecha antes de incluirla en el skeleton.

2. **Ciudad hardcodeada "Bogotá D.C."** en el acta
   - El contrato dice "Cali". Extraer la ciudad del contrato (M2) o dejar `[CIUDAD]`
   - Opción rápida: añadir `city` al `_party_defaults()` con valor `[CIUDAD]` por defecto,
     y que M2 intente extraerla con regex simple (`ciudad de [A-Z][a-z]+`).

---

## Estado del código base al momento de crear esta tarea

**Rama:** `integracion-back-front` (contiene todo lo de abajo mergeado)

**Backend — módulos implementados y testeados:**
- M1: `app/api/routers/ingest.py` — file opcional, usa demo si no hay archivo
- M2: `app/api/routers/extract.py` + `app/domain/extraction/` — regex + LLM fallback
  - Incluye fix del extractor de nombre del trabajador (preamble regex `; y NOMBRE, identificad`)
- M3: `app/api/routers/compliance.py` + `app/domain/gap_rules/` — 5 reglas deterministas
- M4: `app/api/routers/liquidation.py` + `app/domain/liquidation/` — motor ±$1 vs Excel
- M5: `app/api/routers/remediation.py` + `app/domain/remediation/` — skeleton + LLM + validate_figures
- M6: `app/api/routers/dashboard.py` — exposición empresa, alertas
- J2: transcripción con semilla demo + fallback Whisper
- J3: guardián due process — checklist determinista + citation completa
- J4: 3 documentos disciplinarios con veto del guardián
- Tests: 271 passed (ignorando tests/db que tiene dependencia de BD externa)

**Frontend — componentes implementados:**
- `components/compliance/ComplianceFlow.tsx` — wizard actual (M1→M5)
- `components/compliance/Dropzone.tsx` — acepta File real + drag-drop
- `components/compliance/ExtractedRecord.tsx` — 13 campos null-safe
- `components/compliance/GapsList.tsx` — gaps con severity + citation
- `components/compliance/LiquidationTable.tsx` — tabla COP
- `components/compliance/RemediationPanel.tsx` — documento con validación
- `components/compliance/RiskSemaphore.tsx` — semáforo riesgo
- `components/dashboard/DashboardView.tsx` — M6 dashboard empresa
- `lib/api.ts` — todas las funciones de API (M1–M6, J2–J4)
- `lib/types.ts` — todos los tipos TypeScript alineados con backend
- `lib/mocks.ts` — mocks para desarrollo sin backend
- `next.config.ts` — proxy `/api/*` → `http://localhost:8000`
- `.env.local` — `NEXT_PUBLIC_USE_MOCKS=false`, `BACKEND_URL=http://localhost:8000`

**Para arrancar la rama:**
```bash
# Backend
cd cerebro-laboral-hg/backend
.venv/bin/uvicorn app.main:app --port 8000 --log-level warning

# Frontend
cd cerebro-laboral-hg/frontend
npm run dev   # corre en http://localhost:3000
```

---

## Criterios de aceptación

- [ ] Subir un ZIP con 5 contratos → batch_id returned
- [ ] Polling cada 2s muestra progreso en tiempo real (spinner → ✅)
- [ ] Cards aparecen a medida que se completan (no al final)
- [ ] Header muestra: total, en riesgo alto, exposición total acumulada
- [ ] Filtro por severidad y búsqueda por nombre funcionan
- [ ] Clic en card → modal con 4 tabs (datos, riesgos, liquidación, subsanación)
- [ ] El modal reutiliza los componentes existentes (ExtractedRecord, GapsList, etc.)
- [ ] Error en un contrato no detiene el batch (muestra card con ❌ y continúa)
- [ ] Sin archivos → mensaje claro, nunca procesa vacío
