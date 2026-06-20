/**
 * Formateo de dominio. DESIGN.md §7: COP como `$71.175.000` (separador de miles, sin decimales).
 * Toda cifra en UI usa `tnum` (numerales tabulares) además de este formato.
 */

const COP = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });

/** 71175000 -> "$71.175.000". Sin decimales, separador de miles con punto (es-CO). */
export function formatCOP(value: number): string {
  return `$${COP.format(Math.round(value))}`;
}

/** Igual que formatCOP pero acepta el tipo Money del contrato. */
export function formatMoney(money: { value: number }): string {
  return formatCOP(money.value);
}

/** 23.3 -> "23,3%". Porcentaje con coma decimal (es-CO), 1 decimal por defecto. */
export function formatPct(value: number, decimals = 1): string {
  return `${value.toLocaleString("es-CO", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}%`;
}

/** 0.98 -> "98%". Confianza de extracción/OCR como porcentaje entero. */
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/** "2024-12-15" -> "15 dic 2024". Fecha legible es-CO, formato corto. null -> "". */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("es-CO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
