/**
 * Descarga la liquidación como Excel del formato HG.
 * Fuente única: el backend (POST /api/liquidation/export, openpyxl) genera un .xlsx
 * real con la plantilla HG y las MISMAS cifras deterministas de M4. El front solo
 * dispara la descarga del archivo que devuelve el backend.
 */
import { exportLiquidationExcel } from "@/lib/api";
import type { LiquidationRequest } from "@/lib/types";

export async function downloadLiquidationExcel(req: LiquidationRequest): Promise<void> {
  const blob = await exportLiquidationExcel(req);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const name = (req.doc_id || "liquidacion").replace(/[^\w.-]+/g, "_");
  a.href = url;
  a.download = `liquidacion_${name}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
