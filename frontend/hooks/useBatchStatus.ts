"use client";

import { useEffect, useRef, useState } from "react";

import { getBatchStatus } from "@/lib/api";
import type { BatchStatusResponse } from "@/lib/types";

/**
 * Polling del estado de un batch cada `intervalMs`. Se detiene solo cuando
 * `completed === total`. Devuelve el último estado conocido (o null).
 */
export function useBatchStatus(batchId: string | null, intervalMs = 2000) {
  const [status, setStatus] = useState<BatchStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setStatus(null);
    setError(null);
    if (!batchId) return;

    let active = true;
    async function tick() {
      try {
        const s = await getBatchStatus(batchId!);
        if (!active) return;
        setStatus(s);
        if (s.completed >= s.total && timer.current) {
          clearInterval(timer.current);
          timer.current = null;
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Error de red");
      }
    }

    tick(); // primer disparo inmediato
    timer.current = setInterval(tick, intervalMs);
    return () => {
      active = false;
      if (timer.current) clearInterval(timer.current);
    };
  }, [batchId, intervalMs]);

  return { status, error };
}
