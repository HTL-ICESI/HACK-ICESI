/**
 * Guardián del debido proceso (regla determinista de J3, la JOYA).
 * Espejo en cliente del endpoint POST /api/disciplinary/guardian: dado el estado
 * de la diligencia, devuelve si hay riesgo de nulidad, los pasos faltantes con su
 * cita y si se puede proceder. 100% determinista (mismo estado -> misma salida),
 * para que el Guardián frene la nulidad EN VIVO mientras se conduce la diligencia.
 *
 * Cuando el backend de David esté listo, se cambia esta función por la llamada real;
 * la shape (GuardianResponse) es idéntica.
 */
import type {
  Citation,
  DiligenceState,
  GuardianResponse,
  MissingStep,
} from "@/lib/types";

const SUIN = "https://www.suin-juriscol.gov.co/";

function cite(norm_id: string, article: string, title: string): Citation {
  return { norm_id, article, title, url: SUIN, verified: true };
}

interface Rule {
  key: keyof DiligenceState;
  label: string;
  /** Su ausencia genera nulidad (no solo vicio de forma). */
  critical: boolean;
  step: MissingStep;
}

// Pasos del debido proceso disciplinario, en orden de la diligencia.
export const CHECKLIST: Rule[] = [
  {
    key: "charges_read",
    label: "Se leyeron los cargos al trabajador",
    critical: false,
    step: {
      step: "leer_cargos",
      citation: cite("CST", "art. 115", "Procedimiento disciplinario"),
      consequence: "Vicio de forma en el procedimiento",
    },
  },
  {
    key: "worker_notified_right_to_companion",
    label: "Se advirtió el derecho a estar acompañado",
    critical: true,
    step: {
      step: "advertir_derecho_acompanante",
      citation: cite("CN", "art. 29", "Debido proceso"),
      consequence: "Sanción anulable: reintegro + salarios caídos",
    },
  },
  {
    key: "evidence_presented",
    label: "Se presentaron las pruebas",
    critical: false,
    step: {
      step: "presentar_pruebas",
      citation: cite("CST", "art. 115", "Procedimiento disciplinario"),
      consequence: "Debilita el sustento probatorio de la decisión",
    },
  },
  {
    key: "worker_allowed_to_respond",
    label: "Se permitió al trabajador rendir descargos",
    critical: true,
    step: {
      step: "permitir_descargos",
      citation: cite("CST", "art. 115", "Procedimiento disciplinario"),
      consequence: "Nulidad por violación del derecho de defensa",
    },
  },
  {
    key: "term_respected",
    label: "Se respetaron los términos del procedimiento",
    critical: false,
    step: {
      step: "respetar_terminos",
      citation: cite("CST", "art. 115", "Procedimiento disciplinario"),
      consequence: "Extemporaneidad del procedimiento",
    },
  },
];

/** Estado inicial del caso de demostración: faltan dos pasos críticos. */
export const INITIAL_DILIGENCE_STATE: DiligenceState = {
  charges_read: true,
  worker_notified_right_to_companion: false,
  evidence_presented: true,
  worker_allowed_to_respond: false,
  term_respected: true,
};

export function evaluateGuardian(
  session_id: string,
  state: DiligenceState,
): GuardianResponse {
  const missing = CHECKLIST.filter((rule) => !state[rule.key]);
  const nullity = missing.some((rule) => rule.critical);
  return {
    session_id,
    nullity_alert: nullity,
    missing_steps: missing.map((rule) => rule.step),
    // No se puede proceder mientras haya una nulidad pendiente.
    can_proceed: !nullity,
  };
}
