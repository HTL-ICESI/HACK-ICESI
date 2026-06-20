/**
 * Tipos del contrato compartido Backend <-> Frontend.
 * Derivados 1:1 de `icesi-playbook/contracts.json` (v1.1.0). Las shapes están congeladas:
 * keys en inglés, valores de dominio en español. Si cambia el contrato, cambia este archivo.
 *
 * Regla de oro (contracts.json `_meta.rule`): ningún número que alimente una liquidación o el
 * número mágico se emite sin un `source`. Sin source -> el campo no se afirma.
 */

// ── Enums de dominio ────────────────────────────────────────────────────────
export type Severity = "alta" | "media" | "baja";
export type FieldStatus = "ok" | "needs_human" | "not_found";
export type IngestStatus = "digital" | "ocr" | "needs_human";
export type Periodicity = "mensual" | "quincenal" | "anual" | "unica";

// ── Tipos compartidos (shared_types) ────────────────────────────────────────
export interface Money {
  value: number; // COP
  currency: string;
  periodicity?: Periodicity;
}

export interface Source {
  span_start: number;
  span_end: number;
  text: string; // cita textual
  confidence: number; // 0-1
  doc_id: string;
}

export interface Citation {
  norm_id: string;
  article: string;
  title: string;
  url: string;
  verified: boolean;
}

/** Campo trazable: valor + su fuente citada + estado de extracción. */
export interface Field<T> {
  value: T;
  source: Source | null;
  status: FieldStatus;
}

// ── M1 · Ingesta · POST /api/ingest ─────────────────────────────────────────
export interface IngestResponse {
  doc_id: string;
  text: string;
  confidence: number;
  status: IngestStatus;
}

// ── M2 · Extractor con cita · POST /api/extract ─────────────────────────────
export interface Employer {
  name: string;
  nit: string;
}

export interface DocumentRecord {
  employer: Field<Employer>;
  empleado_nombre: Field<string>;
  empleado_documento: Field<string>;
  role: Field<string>;
  vinculo_type: Field<string>;
  base_salary: Field<Money>;
  /** not_found si el contrato no lo menciona (salario > 2 SMLMV). */
  auxilio_transporte: Field<Money | null>;
  /** true si hay comisiones/HE/recargos; false si solo salario básico. */
  salario_variable: Field<boolean>;
  start_date: Field<string>;
  end_date: Field<string>;
  weekly_hours: Field<number>;
  /** not_found (default) si el contrato es indefinido; M3 evalúa el vencimiento. */
  termination_confirmed: Field<boolean | null>;
  /** Dato operativo de nómina (lo proveen M4/M5). null/not_found => no se afirma el gap g5. */
  pago_ss_mora: Field<boolean | null>;
}

export interface ExtractResponse {
  doc_id: string;
  record: DocumentRecord;
}

// ── M3 · Compliance analyze · POST /api/compliance/analyze ───────────────────
export type RemedyType =
  | "otrosi"
  | "contrato_corregido"
  | "instruccion_nomina"
  | "acta_terminacion";

export interface Gap {
  gap_id: string;
  issue: string;
  severity: Severity;
  citation: Citation;
  source: Source | null;
  remedy_type: RemedyType;
}

/**
 * Bloque agregado que alimenta el semáforo del contrato y el orden de la lista.
 * `risk_score = alta*3 + media*2 + baja*1`. `has_blocking_issues=true` si hay algún gap "alta".
 */
export interface ComplianceSummary {
  total_gaps: number;
  by_severity: Record<Severity, number>;
  risk_score: number;
  has_blocking_issues: boolean;
}

export interface ComplianceResponse {
  doc_id: string;
  gaps: Gap[];
  applicable_norms: Citation[];
  summary: ComplianceSummary;
}

// ── M4 · Motor liquidación (determinista) · POST /api/liquidation/compute ────
export type TerminationCause =
  | "renuncia"
  | "justa_causa"
  | "sin_justa_causa"
  | "mutuo_acuerdo"
  | "transaccion";

/**
 * Números planos en COP (no objetos {value, formula}).
 * `total_prestaciones` = cesantías + intereses + prima + vacaciones (lo que el formato HG
 * llama "TOTAL LIQUIDACIÓN"). `indemnizacion` va aparte (0 si renuncia/justa causa).
 * `total` = total_prestaciones + indemnizacion (exposición económica completa).
 */
export interface LiquidationItems {
  cesantias: number;
  intereses_cesantias: number;
  prima: number;
  vacaciones: number;
  total_prestaciones: number;
  indemnizacion: number;
  total: number;
}

export interface LiquidationResponse {
  doc_id: string;
  items: LiquidationItems;
  deterministic: boolean;
  /** Request EXACTO usado (lo adjunta el batch) — permite re-exportar el Excel HG. */
  request?: LiquidationRequest;
}

/** Request real del endpoint M4 (base de liquidación compuesta: básico + variable + auxilio). */
export interface LiquidationRequest {
  doc_id: string;
  monthly_salary: number;
  days_worked: number;
  vinculo_type: string;
  promedio_variable?: number;
  auxilio_transporte?: number;
  dias_pendientes_vacaciones?: number;
  termination_cause?: TerminationCause;
  months_remaining_fixed?: number;
  antiguedad_anios?: number;
  bonificacion?: number;
  // Datos del trabajador y contrato — necesarios para el Excel (formato Liquidacion_Andres)
  nombre_trabajador?: string;
  documento_identidad?: string;
  cargo?: string;
  centro_costos?: string;
  nombre_empresa?: string;
  vinculo_type_label?: string;
  fecha_inicio?: string;        // ISO "2024-03-01"
  fecha_terminacion?: string;
  motivo_terminacion?: string;
  dias_ultimo_periodo?: number;
}

// ── M5 · Generador subsanación · POST /api/remediation/generate ──────────────
export interface FigureUsed {
  label: string;
  value: unknown;
  source: string; // referencia interna, p.ej. "M3.gap.g1"
}

export interface RemediationValidation {
  figures_match_engine: boolean;
  blocked: boolean;
}

export interface RemediationResponse {
  doc_id: string;
  document_type: RemedyType;
  title: string;
  body_markdown: string;
  figures_used: FigureUsed[];
  citations: Citation[];
  validation: RemediationValidation;
}

// ── M6 · Exposición / número mágico · GET /api/dashboard/exposure ────────────
export interface MagicNumber {
  outdated_clauses: number;
  pct_outdated: number;
  cop_exposure: number;
  exposure_formula: string;
  constants: Record<string, string | number>;
}

export type AlertType =
  | "vencimiento_contrato"
  | "vacaciones_vencidas"
  | "seguridad_social_mora";

export interface Alert {
  alert_id: string;
  type: AlertType;
  severity: Severity;
  worker?: string;
  due_date?: string;
  days_left?: number;
  accrued_days?: number;
  amount?: Money;
}

export interface ExposureResponse {
  company_id: string;
  magic_number: MagicNumber;
  alerts: Alert[];
}

// ── J2 · Disciplinario · Transcripción · POST /api/disciplinary/transcribe ───
export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  speaker: string;
}

export interface TranscribeResponse {
  session_id: string;
  transcript: string;
  segments: TranscriptSegment[];
}

// ── J3 · Disciplinario · Guardián (LA JOYA) · POST /api/disciplinary/guardian ─
export interface DiligenceState {
  worker_notified_right_to_companion: boolean;
  charges_read: boolean;
  evidence_presented: boolean;
  worker_allowed_to_respond: boolean;
  term_respected: boolean;
}

export interface MissingStep {
  step: string;
  citation: Citation;
  consequence: string;
}

export interface GuardianResponse {
  session_id: string;
  nullity_alert: boolean;
  missing_steps: MissingStep[];
  can_proceed: boolean;
}

// ── J4 · Disciplinario · Generar documentos · POST /api/disciplinary/documents ─
export type DisciplinaryDocType =
  | "citacion_descargos"
  | "acta_descargos"
  | "decision_final";

export interface DisciplinaryDoc {
  type: DisciplinaryDocType;
  title: string;
  body_markdown: string;
  citations: Citation[];
  blocked_if_nullity?: boolean;
}

export interface DisciplinaryDocsResponse {
  session_id: string;
  documents: DisciplinaryDoc[];
}

// ── BATCH · Procesamiento masivo · /api/batch/* ──────────────────────────────
export type BatchItemStatus = "pending" | "processing" | "done" | "error";

export interface BatchGapBrief {
  gap_id: string;
  issue: string;
  severity: Severity;
  remedy_type: RemedyType;
}

export interface BatchItemSummary {
  worker_name: string;
  employer_name: string;
  risk_level: "alto" | "medio" | "bajo";
  risk_score: number;
  total_exposure: number;
  gap_count: number;
  gaps: BatchGapBrief[];
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
  total: number;
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
  text: string;
  extract: ExtractResponse;
  compliance: ComplianceResponse;
  liquidation: LiquidationResponse;
  remediation: RemediationResponse | null;
}

// ── J1 · Telefonía de descargos (ElevenLabs + Twilio) ────────────────────────

/** Resultado del envío de evidencia por WhatsApp. `preview=true` = sin credenciales
 * Twilio: el backend devuelve el mensaje que se enviaría (demo-safe, no finge). */
export interface EvidenceWhatsAppResult {
  to: string;
  body: string;
  media: string[];
  configured: boolean;
  sent: boolean;
  preview?: boolean;
  error?: string;
  sid?: string;
  status?: string;
}

export interface StartCallResult {
  session_id: string;
  conversation_id?: string | null;
  call_sid?: string | null;
  to: string;
}

/** Un turno de la conversación (agente conduce / trabajador responde). */
export interface CallTurn {
  role: "agente" | "trabajador";
  message: string;
}

/** Resultado REAL de la llamada (ElevenLabs): transcript + descargo + veredicto. */
export interface CallResult {
  conversation_id: string;
  status: string; // "done" | "in-progress" | ...
  transcript: string;
  turns?: CallTurn[];
  descargo: string;
  clasificacion?: string;
  can_proceed?: boolean;
  nullity_alert?: boolean;
}

/** Contraste descargo↔cargos (asesor; el guardián determinista decide el debido proceso). */
export interface DescargoContrast {
  responde: boolean | null;
  cobertura: "total" | "parcial" | "nula" | "no_evaluado";
  puntos_respondidos: string[];
  puntos_sin_responder: string[];
  contradice_evidencia: boolean | null;
  resumen: string;
  evaluado_por: "llm" | "sin_llm";
}
