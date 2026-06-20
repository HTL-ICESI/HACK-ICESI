/**
 * Capa de acceso a datos. Una sola función por endpoint del contrato (contracts.json).
 * Mientras `USE_MOCKS` sea true devuelve los mocks; cuando el backend exista, hace fetch a
 * `${API_URL}<path>`. Las shapes son idénticas, así que cambiar de mock a real es flip de flag.
 *
 * Patrón de toda función: misma firma, mismo tipo de retorno, independiente del origen.
 */

import {
  API_URL,
  USE_MOCKS,
  mockCompliance,
  mockDisciplinaryDocs,
  mockExposure,
  mockExtract,
  mockGuardian,
  mockIngest,
  mockLiquidation,
  mockRemediation,
  mockTranscribe,
} from "@/lib/mocks";
import type {
  BatchIngestResponse,
  BatchResult,
  BatchStatusResponse,
  CallResult,
  ComplianceResponse,
  DescargoContrast,
  EvidenceWhatsAppResult,
  StartCallResult,
  DiligenceState,
  DisciplinaryDocsResponse,
  DocumentRecord,
  ExposureResponse,
  ExtractResponse,
  GuardianResponse,
  IngestResponse,
  LiquidationRequest,
  LiquidationResponse,
  Gap,
  RemediationResponse,
  TranscribeResponse,
} from "@/lib/types";

/**
 * Token multitenant del backend (el token = la empresa). Configurable por entorno;
 * cae al de demo para que funcione de inmediato. Sin él, el backend responde 401.
 */
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "demo-hg-key";

/**
 * M5 (subsanación) y M6 (exposición) aún no están vivos: se quedan en mock aunque se
 * apague USE_MOCKS, hasta que el backend los exponga (NEXT_PUBLIC_M5_M6_LIVE="true").
 */
const M5_M6_LIVE = process.env.NEXT_PUBLIC_M5_M6_LIVE === "true";

/** Latencia simulada para que el mock se sienta como red real en la demo. */
const MOCK_DELAY_MS = 450;

function mock<T>(data: T, delay = MOCK_DELAY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), delay));
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  /** Para multipart (M1 ingest, J2 transcribe). */
  formData?: FormData;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData } = opts;
  // Auth en TODOS los endpoints. En multipart no fijamos Content-Type (el browser pone el boundary).
  const headers: Record<string, string> = { Authorization: `Bearer ${API_KEY}` };
  if (!formData) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: formData ?? (body ? JSON.stringify(body) : undefined),
  });
  if (!res.ok) {
    throw new Error(`API ${method} ${path} -> ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

// ── M1 · POST /api/ingest ────────────────────────────────────────────────────
export async function ingest(file?: File): Promise<IngestResponse> {
  if (USE_MOCKS) return mock(mockIngest);
  const formData = new FormData();
  if (file) formData.append("file", file);
  return request<IngestResponse>("/api/ingest", { method: "POST", formData });
}

// ── M2 · POST /api/extract ───────────────────────────────────────────────────
export async function extract(
  doc_id: string,
  text: string,
): Promise<ExtractResponse> {
  if (USE_MOCKS) return mock(mockExtract);
  return request<ExtractResponse>("/api/extract", {
    method: "POST",
    body: { doc_id, text },
  });
}

// ── M3 · POST /api/compliance/analyze ────────────────────────────────────────
export async function analyzeCompliance(
  doc_id: string,
  record: DocumentRecord,
  doc_type: "contrato" | "RIT" | "politica" = "contrato",
): Promise<ComplianceResponse> {
  if (USE_MOCKS) return mock(mockCompliance);
  return request<ComplianceResponse>("/api/compliance/analyze", {
    method: "POST",
    body: { doc_id, record, doc_type },
  });
}

// ── M4 · POST /api/liquidation/compute ───────────────────────────────────────
export async function computeLiquidation(
  req: LiquidationRequest,
): Promise<LiquidationResponse> {
  if (USE_MOCKS) return mock(mockLiquidation);
  return request<LiquidationResponse>("/api/liquidation/compute", {
    method: "POST",
    body: req,
  });
}

// ── M4 · POST /api/liquidation/export ────────────────────────────────────────
/** Descarga la liquidación como .xlsx real (plantilla HG, openpyxl en el backend). */
export async function exportLiquidationExcel(
  req: LiquidationRequest,
): Promise<Blob> {
  const res = await fetch(`${API_URL}/api/liquidation/export`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`Export liquidación -> ${res.status} ${res.statusText}`);
  }
  return res.blob();
}

// ── M5 · POST /api/remediation/generate ──────────────────────────────────────
export async function generateRemediation(
  doc_id: string,
  gap: Gap,
  liquidation: LiquidationResponse | null,
  doc_type: RemediationResponse["document_type"] = "otrosi",
  record?: DocumentRecord,
): Promise<RemediationResponse> {
  if (USE_MOCKS) return mock(mockRemediation);
  return request<RemediationResponse>("/api/remediation/generate", {
    method: "POST",
    // El backend requiere doc_id. liquidation_data es el dict plano de items,
    // no el wrapper { doc_id, items, deterministic } de M4.
    // record es opcional: si no se pasa, el backend usa [PLACEHOLDER] en el documento.
    body: { doc_id, gap, liquidation: liquidation?.items ?? null, doc_type, record: record ?? null },
  });
}

// ── M6 · GET /api/dashboard/exposure ─────────────────────────────────────────
export async function getExposure(
  company_id = "empresa-001",
): Promise<ExposureResponse> {
  if (USE_MOCKS) return mock(mockExposure, 250);
  return request<ExposureResponse>(
    `/api/dashboard/exposure?company_id=${encodeURIComponent(company_id)}`,
  );
}

// ── J2 · POST /api/disciplinary/transcribe ───────────────────────────────────
export async function transcribe(
  session_id: string,
  audio?: Blob,
): Promise<TranscribeResponse> {
  if (USE_MOCKS) return mock(mockTranscribe);
  const formData = new FormData();
  formData.append("session_id", session_id);
  if (audio) formData.append("audio", audio);
  return request<TranscribeResponse>("/api/disciplinary/transcribe", {
    method: "POST",
    formData,
  });
}

// ── J3 · POST /api/disciplinary/guardian (LA JOYA) ───────────────────────────
export async function guardian(
  session_id: string,
  diligence_state: DiligenceState,
): Promise<GuardianResponse> {
  if (USE_MOCKS) return mock(mockGuardian, 200);
  return request<GuardianResponse>("/api/disciplinary/guardian", {
    method: "POST",
    body: { session_id, diligence_state },
  });
}

// ── J4 · POST /api/disciplinary/documents ────────────────────────────────────
export async function generateDisciplinaryDocs(
  session_id: string,
  diligence_state: DiligenceState,
  transcript: string,
  lawyer_name = "",
  caso?: {
    worker_name?: string;
    worker_id?: string;
    company_name?: string;
    charges?: string;
    diligence_date?: string;
  },
): Promise<DisciplinaryDocsResponse> {
  if (USE_MOCKS) return mock(mockDisciplinaryDocs);
  return request<DisciplinaryDocsResponse>("/api/disciplinary/documents", {
    method: "POST",
    body: { session_id, diligence_state, transcript, lawyer_name, ...(caso ?? {}) },
  });
}

// ── BATCH · Procesamiento masivo ─────────────────────────────────────────────
// Sin mock: el batch es un flujo live (ZIP -> pipeline async -> polling). Requiere
// el backend corriendo (USE_MOCKS no aplica aquí).
export async function batchIngest(files: File[]): Promise<BatchIngestResponse> {
  const formData = new FormData();
  for (const f of files) formData.append("files", f);
  return request<BatchIngestResponse>("/api/batch/ingest", { method: "POST", formData });
}

export async function getBatchStatus(batchId: string): Promise<BatchStatusResponse> {
  return request<BatchStatusResponse>(`/api/batch/status/${encodeURIComponent(batchId)}`);
}

/** Último lote analizado por la empresa (batch_id=null si nunca subió nada). */
export async function getBatchLatest(): Promise<BatchStatusResponse & { batch_id: string | null }> {
  return request<BatchStatusResponse & { batch_id: string | null }>("/api/batch/latest");
}

export async function getBatchResult(batchId: string, docId: string): Promise<BatchResult> {
  return request<BatchResult>(
    `/api/batch/result/${encodeURIComponent(batchId)}/${encodeURIComponent(docId)}`,
  );
}

// ── J1 · Telefonía de descargos (sin mock: flujo live ElevenLabs + Twilio) ───

export interface EvidenceWhatsAppPayload {
  to_number: string;
  worker_name: string;
  company_name: string;
  charges_summary: string;
  /** Si se pasa, el backend arma SOLO los adjuntos firmados desde el expediente. */
  process_id?: string;
  evidence_names?: string[];
  evidence_urls?: string[];
  call_date?: string;
  call_time?: string;
  response_deadline?: string;
  lawyer_name?: string;
}

/** Envía evidencia + párrafo de contexto al WhatsApp del trabajador (Twilio). */
export async function sendEvidenceWhatsApp(
  payload: EvidenceWhatsAppPayload,
): Promise<EvidenceWhatsAppResult> {
  return request<EvidenceWhatsAppResult>("/api/disciplinary/evidence/whatsapp", {
    method: "POST",
    body: payload,
  });
}

/** Envía un documento generado (citación/acta) por WhatsApp como PDF adjunto. */
export async function sendDocumentWhatsApp(payload: {
  to_number: string;
  title: string;
  body_markdown: string;
  worker_name?: string;
  company_name?: string;
}): Promise<{ sent: boolean; preview: string; media?: string[]; sid?: string; note?: string; error?: string }> {
  return request("/api/disciplinary/document/whatsapp", { method: "POST", body: payload });
}

/** Crea un expediente disciplinario y devuelve su process_id. */
export async function createExpediente(payload: {
  worker_name: string;
  worker_id: string;
  employer_name: string;
  contract_type: string;
  doc_id?: string;
}): Promise<{ process_id: string }> {
  return request("/api/disciplinary/expediente", { method: "POST", body: payload });
}

/** Sube un archivo de evidencia al expediente (bytes reales → Twilio los adjunta). */
export async function uploadDisciplinaryEvidence(
  processId: string,
  file: File,
  uploadedBy: string,
): Promise<unknown> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("uploaded_by", uploadedBy || "abogado");
  return request(`/api/disciplinary/${encodeURIComponent(processId)}/evidence`, {
    method: "POST",
    formData,
  });
}

export interface StartCallPayload {
  session_id: string;
  to_number: string;
  company_name: string;
  worker_name: string;
  charges_summary: string;
  evidence_summary: string;
  citation_date: string;
  diligence_date: string;
  defense_term_elapsed: string;
  response_deadline?: string;
  process_type?: string;
  worker_is_unionized?: boolean;
  instructor_name?: string;
}

/** Lanza la llamada de descargos al trabajador (el agente conduce la diligencia). */
export async function startDescargosCall(
  payload: StartCallPayload,
): Promise<StartCallResult> {
  return request<StartCallResult>("/api/disciplinary/call", {
    method: "POST",
    body: payload,
  });
}

/** Trae la transcripción REAL de la llamada de ElevenLabs (polling tras la llamada). */
export async function getCallResult(conversationId: string): Promise<CallResult> {
  return request<CallResult>(
    `/api/disciplinary/call/result/${encodeURIComponent(conversationId)}`,
  );
}

/** Contrasta el descargo del trabajador contra los cargos imputados (Claude). */
export async function contrastDescargo(payload: {
  charges_summary: string;
  evidence_summary?: string;
  descargo_text: string;
}): Promise<DescargoContrast> {
  return request<DescargoContrast>("/api/disciplinary/descargo/contrast", {
    method: "POST",
    body: payload,
  });
}

/** Envía WhatsApp al número indicado notificando vacaciones por vencer. */
export async function notifyVacaciones(payload: {
  to_number: string;
  worker_names: string[];
  company_name?: string;
}): Promise<{ sent: boolean; preview: string; to: string; note?: string }> {
  return request("/api/dashboard/notify-vacations", { method: "POST", body: payload });
}
