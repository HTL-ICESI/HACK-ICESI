"use client";

import { useEffect, useState } from "react";

import { getBatchLatest, getBatchStatus } from "@/lib/api";
import type { BatchItem } from "@/lib/types";

/**
 * Trabajadores REALES de la empresa: los contratos del último lote analizado
 * (M1→M5). Fuente única para el roster de RRHH y el selector del disciplinario,
 * para que ninguna vista invente nombres. Vacío hasta que se sube un lote.
 */
export function useBatchWorkers() {
  const [workers, setWorkers] = useState<BatchItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getBatchLatest()
      .then((r) => {
        if (!active || !r.batch_id) return undefined;
        return getBatchStatus(r.batch_id);
      })
      .then((s) => {
        if (!active) return;
        if (s) {
          setWorkers(s.results.filter((i) => i.status === "done" && i.summary));
        }
        setLoading(false);
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return { workers, loading };
}

/** Un trabajador tiene vacaciones por vencer si su análisis trae el gap g3 (CST art. 186). */
export function tieneVacacionesVencidas(item: BatchItem): boolean {
  return Boolean(item.summary?.gaps.some((g) => g.gap_id === "g3"));
}
