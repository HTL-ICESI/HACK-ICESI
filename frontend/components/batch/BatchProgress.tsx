"use client";

import { CheckCircle2, Loader2, XCircle, Clock } from "lucide-react";

import type { BatchItem, BatchStatusResponse } from "@/lib/types";

const ICON = {
  pending: <Clock className="size-4 text-muted-foreground" aria-hidden />,
  processing: <Loader2 className="size-4 animate-spin text-acento" aria-hidden />,
  done: <CheckCircle2 className="size-4 text-ok-fg" aria-hidden />,
  error: <XCircle className="size-4 text-risk-fg" aria-hidden />,
};

/** Barra de progreso + lista de archivos con su estado en vivo. */
export function BatchProgress({ status }: { status: BatchStatusResponse }) {
  const pct = status.total ? Math.round((status.completed / status.total) * 100) : 0;
  return (
    <div className="rounded-lg border border-n300/60 bg-card p-4 shadow-hairline">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-toga">
          {status.completed} / {status.total} contratos procesados
        </span>
        <span className="font-mono text-muted-foreground">{pct}%</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-n100">
        <div
          className="h-full rounded-full bg-acento transition-[width] duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <ul className="mt-4 max-h-48 space-y-1.5 overflow-y-auto">
        {status.results.map((it: BatchItem) => (
          <li key={it.doc_id} className="flex items-center gap-2 text-xs">
            {ICON[it.status]}
            <span className="truncate text-toga">{it.filename}</span>
            {it.status === "error" && (
              <span className="ml-auto truncate text-risk-fg" title={it.error}>
                error
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
