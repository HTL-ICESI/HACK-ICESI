"use client";

import { useEffect, useRef, useState } from "react";

interface CountUpProps {
  value: number;
  /** Formatea el número en cada frame (p. ej. formatCOP). */
  format: (n: number) => string;
  durationMs?: number;
  className?: string;
}

/**
 * Cuenta desde 0 hasta `value` con easeOutCubic. El money shot entra subiendo.
 * Respeta prefers-reduced-motion: si está activo, muestra el valor final directo.
 */
export function CountUp({
  value,
  format,
  durationMs = 1200,
  className,
}: CountUpProps) {
  const [display, setDisplay] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (reduce) {
      setDisplay(value);
      return;
    }

    let startTs: number | null = null;
    const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

    const tick = (now: number) => {
      if (startTs === null) startTs = now;
      const progress = Math.min((now - startTs) / durationMs, 1);
      setDisplay(value * easeOutCubic(progress));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [value, durationMs]);

  return <span className={className}>{format(Math.round(display))}</span>;
}
