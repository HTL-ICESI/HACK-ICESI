/**
 * Mocks del contrato. Son los `response_example` de `icesi-playbook/contracts.json`,
 * las shapes exactas que devolverá el backend. Mientras `USE_MOCKS` sea true, la capa
 * `lib/api.ts` resuelve con estos objetos; cuando el backend exista, se apunta a
 * `NEXT_PUBLIC_API_URL` y las shapes NO cambian.
 */

import type {
  ComplianceResponse,
  DisciplinaryDocsResponse,
  ExposureResponse,
  ExtractResponse,
  GuardianResponse,
  IngestResponse,
  LiquidationResponse,
  RemediationResponse,
  TranscribeResponse,
} from "@/lib/types";

/** Default true; se apaga con NEXT_PUBLIC_USE_MOCKS="false". */
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

/** Base URL del backend real. Vacío mientras se trabaja contra mocks. */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

// ── M1 · Ingesta ────────────────────────────────────────────────────────────
export const mockIngest: IngestResponse = {
  doc_id: "contrato-001",
  text: "CONTRATO INDIVIDUAL DE TRABAJO A TERMINO FIJO... salario mensual de DOS MILLONES QUINIENTOS MIL PESOS...",
  confidence: 0.97,
  status: "digital",
};

// ── M2 · Extractor con cita ─────────────────────────────────────────────────
export const mockExtract: ExtractResponse = {
  doc_id: "contrato-001",
  record: {
    employer: {
      value: { name: "Empresa Cliente SAS", nit: "900123456-7" },
      source: null,
      status: "ok",
    },
    empleado_nombre: {
      value: "JUAN PEREZ",
      source: {
        span_start: 90,
        span_end: 112,
        text: "Trabajador: JUAN PEREZ",
        confidence: 0.95,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    empleado_documento: {
      value: "1144000000",
      source: {
        span_start: 113,
        span_end: 133,
        text: "C.C. 1.144.000.000",
        confidence: 0.99,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    role: {
      value: "Asesor comercial",
      source: {
        span_start: 250,
        span_end: 280,
        text: "cargo de Asesor comercial",
        confidence: 0.92,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    vinculo_type: {
      value: "termino_fijo",
      source: {
        span_start: 340,
        span_end: 372,
        text: "contrato a termino fijo de un (1) ano",
        confidence: 0.95,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    base_salary: {
      value: { value: 2500000, currency: "COP", periodicity: "mensual" },
      source: {
        span_start: 1820,
        span_end: 1875,
        text: "salario mensual de DOS MILLONES QUINIENTOS MIL PESOS",
        confidence: 0.98,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    auxilio_transporte: {
      value: { value: 249095, currency: "COP", periodicity: "mensual" },
      source: {
        span_start: 1900,
        span_end: 1942,
        text: "auxilio de transporte: 249.095",
        confidence: 0.97,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    salario_variable: {
      value: false,
      source: null,
      status: "ok",
    },
    start_date: {
      value: "2024-02-01",
      source: {
        span_start: 410,
        span_end: 440,
        text: "a partir del 1 de febrero de 2024",
        confidence: 0.96,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    end_date: {
      value: "2025-01-31",
      source: {
        span_start: 442,
        span_end: 470,
        text: "hasta el 31 de enero de 2025",
        confidence: 0.94,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    weekly_hours: {
      value: 48,
      source: {
        span_start: 980,
        span_end: 1010,
        text: "jornada de cuarenta y ocho horas",
        confidence: 0.9,
        doc_id: "contrato-001",
      },
      status: "ok",
    },
    termination_confirmed: {
      value: false,
      source: null,
      status: "ok",
    },
    // Dato operativo de nómina: M2 no lo llena -> not_found honesto (ámbar), nunca inventado.
    pago_ss_mora: {
      value: null,
      source: null,
      status: "not_found",
    },
  },
};

// ── M3 · Compliance analyze ─────────────────────────────────────────────────
export const mockCompliance: ComplianceResponse = {
  doc_id: "contrato-001",
  gaps: [
    {
      gap_id: "g1",
      issue:
        "Jornada de 48h no actualizada a 42h (Ley 2101/2021, vigor pleno 2026)",
      severity: "alta",
      citation: {
        norm_id: "Ley 2101",
        article: "art. 3",
        title: "Reduccion jornada a 42h",
        url: "https://www.suin-juriscol.gov.co/",
        verified: false,
      },
      source: {
        span_start: 980,
        span_end: 1010,
        text: "jornada de cuarenta y ocho horas",
        confidence: 0.9,
        doc_id: "contrato-001",
      },
      remedy_type: "otrosi",
    },
    {
      gap_id: "g2",
      issue: "Posible reclasificacion: indicios de subordinacion (Ley 2466/2025)",
      severity: "media",
      citation: {
        norm_id: "Ley 2466",
        article: "art. 5",
        title: "Subordinacion algoritmica",
        url: "https://www.suin-juriscol.gov.co/",
        verified: false,
      },
      source: null,
      remedy_type: "contrato_corregido",
    },
  ],
  applicable_norms: [
    {
      norm_id: "CST",
      article: "art. 64",
      title: "Indemnizacion despido sin justa causa",
      url: "https://www.suin-juriscol.gov.co/",
      verified: true,
    },
  ],
  // Alimenta el semáforo del contrato: risk_score = alta*3 + media*2 + baja*1.
  summary: {
    total_gaps: 2,
    by_severity: { alta: 1, media: 1, baja: 0 },
    risk_score: 5,
    has_blocking_issues: true,
  },
};

// ── M4 · Motor liquidación (determinista) ───────────────────────────────────
// Items planos en COP (no objetos). Caso gold real de HG (José Ospino), al centavo.
// total_prestaciones = cesantías+intereses+prima+vacaciones; indemnizacion aparte (0 si renuncia).
export const mockLiquidation: LiquidationResponse = {
  doc_id: "contrato-001",
  items: {
    cesantias: 490743.85,
    intereses_cesantias: 10796.36,
    prima: 490743.85,
    vacaciones: 728306.88,
    total_prestaciones: 1720590.94,
    indemnizacion: 0.0,
    total: 1720590.94,
  },
  deterministic: true,
};

// ── M5 · Generador subsanación ──────────────────────────────────────────────
export const mockRemediation: RemediationResponse = {
  doc_id: "contrato-001",
  document_type: "otrosi",
  title: "Otrosi No. 1 - Ajuste de jornada laboral a 42 horas",
  body_markdown:
    "Entre Empresa Cliente SAS... se modifica la clausula de jornada a CUARENTA Y DOS (42) horas semanales, conforme a la Ley 2101 de 2021...",
  figures_used: [{ label: "jornada_nueva", value: 42, source: "M3.gap.g1" }],
  citations: [
    {
      norm_id: "Ley 2101",
      article: "art. 3",
      title: "Reduccion jornada",
      url: "https://www.suin-juriscol.gov.co/",
      verified: false,
    },
  ],
  validation: { figures_match_engine: true, blocked: false },
};

// ── M6 · Exposición / número mágico ─────────────────────────────────────────
export const mockExposure: ExposureResponse = {
  company_id: "empresa-001",
  magic_number: {
    outdated_clauses: 7,
    pct_outdated: 23.3,
    cop_exposure: 71175000,
    exposure_formula:
      "trabajadores_en_riesgo(50) * SMLMV_2026(1423500) + reliquidaciones_detectadas",
    constants: {
      SMLMV_2026: 1423500,
      mora_factor_art65: "1 dia salario por dia de mora",
    },
  },
  alerts: [
    {
      alert_id: "a1",
      type: "vencimiento_contrato",
      worker: "***",
      due_date: "2024-12-15",
      days_left: 14,
      severity: "alta",
    },
    {
      alert_id: "a2",
      type: "vacaciones_vencidas",
      worker: "***",
      accrued_days: 31,
      severity: "media",
    },
    {
      alert_id: "a3",
      type: "seguridad_social_mora",
      amount: { value: 480000, currency: "COP" },
      due_date: "2024-12-10",
      severity: "alta",
    },
  ],
};

// ── J2 · Disciplinario · Transcripción ──────────────────────────────────────
export const mockTranscribe: TranscribeResponse = {
  session_id: "desc-001",
  transcript:
    "Siendo las 10 am se da inicio a la diligencia de descargos del trabajador...",
  segments: [
    {
      start: 0.0,
      end: 5.2,
      text: "Siendo las 10 am se da inicio...",
      speaker: "instructor",
    },
  ],
};

// ── J3 · Disciplinario · Guardián (LA JOYA) ─────────────────────────────────
export const mockGuardian: GuardianResponse = {
  session_id: "desc-001",
  nullity_alert: true,
  missing_steps: [
    {
      step: "advertir_derecho_acompanante",
      citation: {
        norm_id: "CN",
        article: "art. 29",
        title: "Debido proceso",
        url: "https://www.suin-juriscol.gov.co/",
        verified: true,
      },
      consequence: "Sancion anulable: reintegro + salarios caidos",
    },
    {
      step: "permitir_descargos",
      citation: {
        norm_id: "CST",
        article: "art. 115",
        title: "Procedimiento disciplinario",
        url: "https://www.suin-juriscol.gov.co/",
        verified: true,
      },
      consequence: "Nulidad por violacion del derecho de defensa",
    },
  ],
  can_proceed: false,
};

// ── J4 · Disciplinario · Generar 3 documentos ───────────────────────────────
export const mockDisciplinaryDocs: DisciplinaryDocsResponse = {
  session_id: "desc-001",
  documents: [
    {
      type: "citacion_descargos",
      title: "Citacion a descargos",
      body_markdown:
        "Por medio de la presente se cita al trabajador a diligencia de descargos...",
      citations: [],
    },
    {
      type: "acta_descargos",
      title: "Acta de la diligencia de descargos",
      body_markdown:
        "Siendo las 10:00 a.m. se da inicio a la diligencia de descargos...",
      citations: [],
    },
    {
      type: "decision_final",
      title: "Decision final",
      body_markdown:
        "Documento bloqueado: existe una nulidad pendiente en el debido proceso.",
      citations: [],
      blocked_if_nullity: true,
    },
  ],
};
