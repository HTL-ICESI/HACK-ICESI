"use client";

import { useEffect, useState } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { usePersona } from "@/components/shell/persona-context";
import { StatusBadge } from "@/components/thesis/StatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { getExposure } from "@/lib/api";
import { formatCOP, formatPct } from "@/lib/format";
import type { ExposureResponse } from "@/lib/types";
import { AlertsPanel } from "./AlertsPanel";
import { CountUp } from "./CountUp";
import { ExposureBreakdown } from "./ExposureBreakdown";
import { RrhhHome } from "./RrhhHome";

function DashboardSkeleton() {
  return (
    <div className="flex flex-wrap gap-5">
      <Skeleton className="h-72 flex-[3_1_440px] rounded-2xl" />
      <div className="flex flex-[1_1_260px] flex-col gap-5">
        <Skeleton className="h-32 rounded-2xl" />
        <Skeleton className="h-32 rounded-2xl" />
      </div>
      <Skeleton className="h-56 w-full rounded-2xl" />
    </div>
  );
}

function AbogadoDashboard({ data }: { data: ExposureResponse }) {
  const m = data.magic_number;
  const totalClauses = Math.round(m.outdated_clauses / (m.pct_outdated / 100));

  return (
    <TooltipProvider delayDuration={150} skipDelayDuration={0}>
      <header className="mb-8">
        <h1 className="font-display text-3xl font-medium text-toga">
          Exposición en riesgo
        </h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Exposición consolidada, con su fórmula y fuentes.
        </p>
      </header>

      <div className="flex flex-wrap items-start gap-5">
        {/* Hero money shot */}
        <Card className="flex-[3_1_440px] border-n300/60 shadow-bezel">
          <CardContent className="p-7">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Exposición en riesgo
              </span>
              <StatusBadge kind="calculado" />
            </div>

            <div className="mt-3.5 flex flex-wrap items-end gap-x-3.5 gap-y-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex cursor-help">
                    <CountUp
                      value={m.cop_exposure}
                      format={formatCOP}
                      className="font-display text-[clamp(2.5rem,7vw,4rem)] leading-[0.92] tracking-tight text-toga tnum"
                    />
                  </span>
                </TooltipTrigger>
                <TooltipContent>
                  <span className="font-mono">{m.exposure_formula}</span>
                </TooltipContent>
              </Tooltip>
            </div>

            <div className="mt-6">
              <ExposureBreakdown total={m.cop_exposure} />
            </div>

            <p className="mt-5 border-t border-n300/50 pt-4 font-mono text-xs text-muted-foreground/80">
              {m.exposure_formula}
            </p>
          </CardContent>
        </Card>

        {/* Rail de métricas secundarias */}
        <div className="flex flex-[1_1_260px] flex-col gap-5">
          <Card className="border-n300/60 shadow-hairline">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <span className="text-[13px] font-medium text-muted-foreground">
                  Cláusulas desactualizadas
                </span>
                <StatusBadge kind="calculado" />
              </div>
              <div className="mt-2.5 flex items-baseline gap-2">
                <CountUp
                  value={m.outdated_clauses}
                  format={String}
                  className="font-display text-[2.5rem] leading-none text-toga tnum"
                />
                <span className="text-sm text-muted-foreground">
                  de {totalClauses}
                </span>
              </div>
              <div className="mt-3.5 h-2 overflow-hidden rounded-full bg-n100">
                <span
                  className="block h-full origin-left animate-grow-x rounded-full bg-acento"
                  style={{ width: `${m.pct_outdated}%` }}
                />
              </div>
              <p className="mt-2 text-[13px] text-muted-foreground">
                {formatPct(m.pct_outdated)} del clausulado
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Alertas */}
        <AlertsPanel alerts={data.alerts} className="w-full" />
      </div>
    </TooltipProvider>
  );
}

export function DashboardView() {
  const { company, persona } = usePersona();
  const [data, setData] = useState<ExposureResponse | null>(null);
  const [status, setStatus] = useState<"loading" | "error" | "ready">(
    "loading",
  );
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus("loading");
    getExposure(company.id)
      .then((res) => {
        if (active) {
          setData(res);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [company.id, reloadKey]);

  const retry = () => setReloadKey((k) => k + 1);

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 md:py-10">
      {status === "loading" ? (
        <DashboardSkeleton />
      ) : status === "error" || !data ? (
        <ErrorState
          message="No pudimos cargar la exposición de esta empresa."
          onRetry={retry}
        />
      ) : persona === "rrhh" ? (
        <RrhhHome companyName={company.name} alerts={data.alerts} />
      ) : (
        <AbogadoDashboard data={data} />
      )}
    </div>
  );
}
