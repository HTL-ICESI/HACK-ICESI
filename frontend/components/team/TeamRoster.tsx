"use client";

import { Users } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { RISK_STYLE } from "@/components/batch/risk";
import { useBatchWorkers, tieneVacacionesVencidas } from "@/hooks/useBatchWorkers";
import { formatCOP } from "@/lib/format";
import type { BatchItem } from "@/lib/types";
import { cn } from "@/lib/utils";

function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

/** Tarjeta de trabajador derivada del análisis real (M3 gaps + M4 exposición). */
export function TeamCard({ item }: { item: BatchItem }) {
  const s = item.summary!;
  const risk = RISK_STYLE[s.risk_level];
  const overdueVacaciones = tieneVacacionesVencidas(item);

  return (
    <div className="rounded-2xl border border-n300/60 bg-card p-5 shadow-hairline transition-colors hover:border-acento/40">
      <div className="flex items-center gap-3">
        <Avatar className="size-10">
          <AvatarFallback className="bg-acento-soft font-mono text-acento">
            {initials(s.worker_name)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-toga">
            {s.worker_name}
          </p>
          <p className="truncate text-xs text-muted-foreground">
            {s.employer_name}
          </p>
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium",
            risk.chip,
          )}
        >
          <span className={cn("size-1.5 rounded-full", risk.dot)} />
          {risk.label}
        </span>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-n300/50 pt-3">
        <span className="text-[13px] text-[#554B45]">
          <span className="font-semibold text-toga tnum">{s.gap_count}</span>{" "}
          {s.gap_count === 1 ? "hallazgo" : "hallazgos"}
          {overdueVacaciones && (
            <span className="ml-2 font-mono text-[11px] text-warn-fg">
              vacaciones por vencer
            </span>
          )}
        </span>
        <span className="font-mono text-[11px] text-muted-foreground tnum">
          {formatCOP(s.total_exposure)}
        </span>
      </div>
    </div>
  );
}

/** Roster de equipo: trabajadores reales del último lote analizado. */
export function TeamRoster() {
  const { workers, loading } = useBatchWorkers();

  if (loading) {
    return (
      <section>
        <div className="mb-4 h-5 w-24 animate-pulse rounded bg-n100" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32 rounded-2xl" />
          ))}
        </div>
      </section>
    );
  }

  if (workers.length === 0) {
    return (
      <section>
        <h2 className="mb-4 text-base font-semibold text-toga">Equipo</h2>
        <EmptyState
          icon={Users}
          title="Aún no hay trabajadores analizados"
          hint="Sube los contratos en Compliance para ver aquí al equipo."
        />
      </section>
    );
  }

  const withOverdue = workers.filter(tieneVacacionesVencidas).length;

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-toga">Equipo</h2>
        <p className="text-xs text-muted-foreground">
          {workers.length} {workers.length === 1 ? "trabajador" : "trabajadores"}{" "}
          analizados
          {withOverdue > 0 && (
            <>
              {" · "}
              <span className="font-medium text-warn-fg">{withOverdue}</span> con
              vacaciones por vencer
            </>
          )}
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {workers.map((item) => (
          <TeamCard key={item.doc_id} item={item} />
        ))}
      </div>
    </section>
  );
}
