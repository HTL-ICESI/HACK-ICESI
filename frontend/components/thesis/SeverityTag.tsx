import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/types";

/**
 * Pill de severidad (DESIGN.md §4): alta=rojo · media=ámbar · baja=gris.
 * Consistente en toda la app. El color es estado, no decoración.
 */
const MAP: Record<Severity, { cls: string; label: string }> = {
  alta: { cls: "bg-risk-soft text-risk-fg", label: "alta" },
  media: { cls: "bg-warn-soft text-warn-fg", label: "media" },
  baja: { cls: "bg-n100 text-[#554B45]", label: "baja" },
};

interface SeverityTagProps {
  severity: Severity;
  className?: string;
}

export function SeverityTag({ severity, className }: SeverityTagProps) {
  const { cls, label } = MAP[severity];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        cls,
        className,
      )}
    >
      {label}
    </span>
  );
}
