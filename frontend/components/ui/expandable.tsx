"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";

import { panelTween } from "@/lib/motion";

interface ExpandableProps {
  /** Controlado desde fuera; el disparador (botón) vive en el consumidor. */
  open: boolean;
  children: React.ReactNode;
  /** Clases para el contenedor animado (no pongas margin-top: usa padding). */
  className?: string;
  /** id para enlazar con `aria-controls` del disparador externo. */
  id?: string;
}

/**
 * Expand/collapse de altura suave (patrón cult-ui `expandable`, re-tonalizado).
 * Anima `height: auto` + opacidad con la curva drawer HG. Sin rebote — sobrio.
 * Respeta `prefers-reduced-motion`: muestra/oculta sin animar la altura.
 * El contenido se desmonta al colapsar (no queda en el árbol accesible).
 */
export function Expandable({ open, children, className, id }: ExpandableProps) {
  const reduce = useReducedMotion();

  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.div
          key="content"
          id={id}
          initial={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
          animate={
            reduce ? { opacity: 1 } : { height: "auto", opacity: 1 }
          }
          exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
          transition={reduce ? { duration: 0 } : panelTween}
          style={{ overflow: "hidden" }}
          className={className}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
