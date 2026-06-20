"use client";

import { ArrowRight } from "lucide-react";

import { formatCOP } from "@/lib/format";
import type { BatchItem } from "@/lib/types";
import { RISK_STYLE } from "./risk";

/** Card de un contrato procesado en el lote. Clic → abre el detalle completo. */
export function ContractCard({ item, onOpen }: { item: BatchItem; onOpen: () => void }) {
  const s = item.summary;
  if (!s) return null;
  const style = RISK_STYLE[s.risk_level];

  return (
    <button
      onClick={onOpen}
      className="group flex w-full flex-col rounded-lg border border-n300/60 bg-card p-3 text-left shadow-hairline transition-colors hover:border-acento/40"
    >
      <div className="flex items-center justify-between gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${style.chip}`}
        >
          <span className={`size-1.5 rounded-full ${style.dot}`} aria-hidden />
          {style.label}
        </span>
        <span className="text-[10px] font-mono text-muted-foreground">
          {s.gap_count} {s.gap_count === 1 ? "riesgo" : "riesgos"}
        </span>
      </div>

      <p className="mt-2 truncate font-display text-[13px] font-medium text-toga">
        {s.worker_name}
      </p>

      <div className="mt-2 flex items-end justify-between border-t border-n300/50 pt-2">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
            Exposición si se termina
          </p>
          <p className="font-mono text-[13px] font-medium text-toga">{formatCOP(s.total_exposure)}</p>
        </div>
        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-acento group-hover:gap-1.5">
          Ver <ArrowRight className="size-3" aria-hidden />
        </span>
      </div>
    </button>
  );
}
