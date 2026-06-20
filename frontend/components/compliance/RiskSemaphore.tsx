import type { ComplianceSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Tone {
  dot: string;
  soft: string;
  fg: string;
  label: string;
}

/** Semáforo del contrato derivado del bloque `summary` de M3. El color es estado, no decoración. */
function toneFor(summary: ComplianceSummary): Tone {
  if (summary.has_blocking_issues) {
    return { dot: "bg-risk", soft: "bg-risk-soft", fg: "text-risk-fg", label: "Riesgo alto" };
  }
  if (summary.risk_score > 0) {
    return { dot: "bg-warn", soft: "bg-warn-soft", fg: "text-warn-fg", label: "Riesgo medio" };
  }
  return { dot: "bg-ok", soft: "bg-ok-soft", fg: "text-ok-fg", label: "Sin riesgos" };
}

export function RiskSemaphore({ summary }: { summary: ComplianceSummary }) {
  const tone = toneFor(summary);
  const { alta, media, baja } = summary.by_severity;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg px-4 py-3",
        tone.soft,
      )}
    >
      <span className="flex items-center gap-2">
        <span className={cn("size-2.5 rounded-full", tone.dot)} aria-hidden="true" />
        <span className={cn("text-sm font-semibold", tone.fg)}>{tone.label}</span>
      </span>
      <span className="font-mono text-xs text-muted-foreground tnum">
        nivel de riesgo {summary.risk_score}
      </span>
      <span className="ml-auto flex items-center gap-3 font-mono text-xs tnum">
        <span className="text-risk">{alta} alta</span>
        <span className="text-warn">{media} media</span>
        <span className="text-muted-foreground">{baja} baja</span>
      </span>
    </div>
  );
}

/** Punto + etiqueta compactos para el "recibo" colapsado del paso. */
export function RiskDot({ summary }: { summary: ComplianceSummary }) {
  const tone = toneFor(summary);
  return (
    <span className="flex items-center gap-2 text-sm text-muted-foreground">
      <span className={cn("size-2 rounded-full", tone.dot)} aria-hidden="true" />
      {summary.total_gaps} hallazgos
    </span>
  );
}
