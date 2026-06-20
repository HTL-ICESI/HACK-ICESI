import { cn } from "@/lib/utils";
import { formatCOP } from "@/lib/format";

interface MoneyProps {
  value: number;
  className?: string;
}

/**
 * Cifra de plata en carbón HG con numerales tabulares.
 * El formato es `$71.175.000` (sin decimales). Para el money shot, pásale
 * un tamaño grande vía className (p.ej. `text-money font-display`).
 */
export function Money({ value, className }: MoneyProps) {
  return (
    <span className={cn("tnum font-medium text-toga", className)}>
      {formatCOP(value)}
    </span>
  );
}
