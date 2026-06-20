"use client";

import { formatCOP } from "@/lib/format";
import type { BatchItem } from "@/lib/types";

/** Métricas agregadas del lote, derivadas de los summaries ya completados. */
export function BatchDashboardHeader({ items }: { items: BatchItem[] }) {
  const done = items.filter((i) => i.summary);
  const enRiesgoAlto = done.filter((i) => i.summary!.risk_level === "alto").length;
  const exposicion = done.reduce((acc, i) => acc + (i.summary!.total_exposure || 0), 0);

  const metrics = [
    { label: "Contratos analizados", value: String(done.length), tone: "text-toga" },
    { label: "En riesgo alto", value: String(enRiesgoAlto), tone: "text-risk-fg" },
    { label: "Exposición total", value: formatCOP(exposicion), tone: "text-toga" },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {metrics.map((m) => (
        <div
          key={m.label}
          className="rounded-lg border border-n300/60 bg-card p-4 shadow-hairline"
        >
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{m.label}</p>
          <p className={`mt-1 font-display text-2xl font-medium ${m.tone}`}>{m.value}</p>
        </div>
      ))}
    </div>
  );
}
