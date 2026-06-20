/**
 * Construye un LiquidationRequest a partir del extract de un contrato.
 *
 * Fuente preferida para el Excel HG es el `request` EXACTO que adjunta el batch
 * (`liquidation.request`). Pero los lotes antiguos persistidos no lo traen, así
 * que este helper reconstruye un request válido desde `extract.record` para que
 * el botón "Descargar Excel" siempre funcione (mismos campos del contrato +
 * constantes de caso para lo que el contrato no especifica).
 */
import type { ExtractResponse, LiquidationRequest } from "@/lib/types";

// Valores de caso para los campos que el contrato no declara (días del último
// período, promedio variable, causa de terminación demo).
const CASE = {
  days_worked: 66,
  promedio_variable: 676784.614,
  dias_pendientes_vacaciones: 9,
  termination_cause: "renuncia" as const,
};

export function liquidationRequest(ext: ExtractResponse): LiquidationRequest {
  const r = ext.record;
  const aux =
    r.auxilio_transporte.status === "ok" && r.auxilio_transporte.value
      ? r.auxilio_transporte.value.value
      : 0;
  return {
    doc_id: ext.doc_id,
    monthly_salary: r.base_salary.value.value,
    days_worked: CASE.days_worked,
    vinculo_type: r.vinculo_type.value,
    promedio_variable: CASE.promedio_variable,
    auxilio_transporte: aux,
    dias_pendientes_vacaciones: CASE.dias_pendientes_vacaciones,
    termination_cause: CASE.termination_cause,
  };
}
