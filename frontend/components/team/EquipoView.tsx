"use client";

import { useEffect, useState } from "react";

import { AlertsPanel } from "@/components/dashboard/AlertsPanel";
import { ErrorState } from "@/components/common/ErrorState";
import { usePersona } from "@/components/shell/persona-context";
import { Skeleton } from "@/components/ui/skeleton";
import { getExposure } from "@/lib/api";
import type { Alert } from "@/lib/types";
import { TeamRoster } from "./TeamRoster";

export function EquipoView() {
  const { company } = usePersona();
  const [alerts, setAlerts] = useState<Alert[]>([]);
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
          setAlerts(res.alerts);
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
      <header className="mb-8">
        <h1 className="font-display text-3xl font-medium text-toga">
          Alertas y equipo
        </h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Lo que requiere acción en {company.name}: qué hacer y cuándo, sin
          jerga.
        </p>
      </header>

      <div className="space-y-8">
        {status === "loading" ? (
          <Skeleton className="h-56 rounded-lg" />
        ) : status === "error" ? (
          <ErrorState
            message="No pudimos cargar las alertas de esta empresa."
            onRetry={retry}
          />
        ) : (
          <AlertsPanel alerts={alerts} />
        )}
        <TeamRoster />
      </div>
    </div>
  );
}
