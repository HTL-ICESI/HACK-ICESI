"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { easeSnappy } from "@/lib/motion";
import { cn } from "@/lib/utils";

/**
 * Tips rotando durante un proceso largo (patrón cult-ui `loading-carousel`,
 * reconstruido ligero — sin embla ni imágenes). Convierte la espera del análisis
 * en un momento de confianza: muestra QUÉ está haciendo el motor, reforzando la
 * historia anti-alucinación (cada dato con su fuente).
 * Sobrio y accesible: el texto rotando es `aria-hidden`; un `role="status"`
 * estable anuncia una sola vez a lectores de pantalla.
 */

const DEFAULT_TIPS = [
  "Leyendo el documento…",
  "Identificando cláusulas y vínculos…",
  "Cotejando contra el CST y la jurisprudencia…",
  "Validando cada dato con su fuente…",
  "Calculando la liquidación con su fórmula…",
];

interface ProcessingTipsProps {
  tips?: string[];
  /** Milisegundos por tip. */
  intervalMs?: number;
  /** Etiqueta estable para lectores de pantalla. */
  srLabel?: string;
  className?: string;
}

const textVariants = {
  enter: { opacity: 0, y: 6 },
  center: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -6 },
};

export function ProcessingTips({
  tips = DEFAULT_TIPS,
  intervalMs = 2200,
  srLabel = "Analizando el documento, un momento…",
  className,
}: ProcessingTipsProps) {
  const [index, setIndex] = useState(0);
  const reduce = useReducedMotion();

  useEffect(() => {
    const id = setInterval(
      () => setIndex((prev) => (prev + 1) % tips.length),
      intervalMs,
    );
    return () => clearInterval(id);
  }, [tips.length, intervalMs]);

  const current = tips[index];

  return (
    <div className={cn("flex w-full flex-col items-center gap-3", className)}>
      <span className="sr-only" role="status" aria-live="polite">
        {srLabel}
      </span>

      <div
        aria-hidden="true"
        className="flex min-h-[1.5rem] items-center justify-center"
      >
        {reduce ? (
          <p className="text-sm font-medium text-toga">{current}</p>
        ) : (
          <AnimatePresence mode="wait" initial={false}>
            <motion.p
              key={index}
              variants={textVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.28, ease: easeSnappy }}
              className="text-sm font-medium text-toga"
            >
              {current}
            </motion.p>
          </AnimatePresence>
        )}
      </div>

      {/* Línea de progreso por tip; se reinicia con cada uno. */}
      <div
        aria-hidden="true"
        className="h-0.5 w-32 overflow-hidden rounded-full bg-n100"
      >
        {reduce ? (
          <span className="block h-full w-1/2 bg-acento/60" />
        ) : (
          <motion.span
            key={index}
            className="block h-full bg-acento/70"
            initial={{ width: "0%" }}
            animate={{ width: "100%" }}
            transition={{ duration: intervalMs / 1000, ease: "linear" }}
          />
        )}
      </div>
    </div>
  );
}
