"use client";

import { useReducedMotion } from "motion/react";

import { cn } from "@/lib/utils";

/**
 * Fondo de marca de la landing: el átomo del logo WorkLab (órbitas + electrones)
 * sobre un halo rojo HG que respira y deriva, detrás de TODO el contenido.
 * Da profundidad y recordación al hacer scroll; nunca compite con el texto
 * (fixed · pointer-events-none · aria-hidden). Respeta prefers-reduced-motion:
 * sin giro ni deriva, solo la atmósfera estática.
 */
export function AtomBackground({ className }: { className?: string }) {
  const reduce = useReducedMotion();
  const spinA = reduce ? "" : "animate-[spin_150s_linear_infinite]";
  const spinB = reduce ? "" : "animate-[spin_110s_linear_infinite_reverse]";
  const orbit = "origin-center [transform-box:fill-box]";

  return (
    <div
      aria-hidden="true"
      className={cn(
        "pointer-events-none fixed inset-0 -z-10 overflow-hidden",
        className,
      )}
    >
      {/* Profundidad de página: degradé muy suave desde arriba (no el bloque plano). */}
      <div className="absolute inset-0 bg-[radial-gradient(120%_85%_at_50%_-12%,rgba(128,24,23,0.12),transparent_56%)] dark:bg-[radial-gradient(120%_85%_at_50%_-12%,rgba(224,122,114,0.12),transparent_52%)]" />

      {/* Halo rojo HG protagonista: respira y deriva muy lento. */}
      <div
        className={cn(
          "absolute left-[60%] top-[-14%] h-[72vmax] w-[72vmax] -translate-x-1/2 rounded-full blur-[120px]",
          "bg-[radial-gradient(circle,rgba(128,24,23,0.30),transparent_62%)] dark:bg-[radial-gradient(circle,rgba(128,24,23,0.55),transparent_60%)]",
          reduce ? "" : "animate-drift",
        )}
      />
      {/* Halo neutral frío para equilibrar (muy tenue). */}
      <div
        className={cn(
          "absolute bottom-[-18%] left-[-8%] h-[58vmax] w-[58vmax] rounded-full blur-[120px]",
          "bg-[radial-gradient(circle,rgba(53,53,53,0.05),transparent_60%)] dark:bg-[radial-gradient(circle,rgba(199,192,186,0.06),transparent_60%)]",
          reduce ? "" : "animate-breathe",
        )}
      />

      {/* Átomo: órbitas + electrones, centrado, girando muy lento. */}
      <svg
        viewBox="0 0 600 600"
        fill="none"
        className="absolute left-1/2 top-1/2 h-[155vmax] w-[155vmax] -translate-x-1/2 -translate-y-1/2 text-acento opacity-[0.72] dark:opacity-[0.7]"
      >
        {/* Grupo A: dos órbitas cruzadas + 2 electrones. */}
        <g className={cn(orbit, spinA)} stroke="currentColor">
          <ellipse
            cx="300"
            cy="300"
            rx="272"
            ry="104"
            transform="rotate(22 300 300)"
            strokeWidth="1.4"
            strokeOpacity="0.18"
          />
          <ellipse
            cx="300"
            cy="300"
            rx="272"
            ry="104"
            transform="rotate(-22 300 300)"
            strokeWidth="1.4"
            strokeOpacity="0.18"
          />
          <circle
            cx="572"
            cy="300"
            r="6"
            transform="rotate(22 300 300)"
            fill="currentColor"
            fillOpacity="0.55"
          />
          <circle
            cx="28"
            cy="300"
            r="5"
            transform="rotate(-22 300 300)"
            fill="currentColor"
            fillOpacity="0.45"
          />
        </g>

        {/* Grupo B: una órbita casi vertical, contrarrotando + 1 electrón. */}
        <g className={cn(orbit, spinB)} stroke="currentColor">
          <ellipse
            cx="300"
            cy="300"
            rx="270"
            ry="86"
            transform="rotate(90 300 300)"
            strokeWidth="1.4"
            strokeOpacity="0.14"
          />
          <circle
            cx="570"
            cy="300"
            r="5"
            transform="rotate(90 300 300)"
            fill="currentColor"
            fillOpacity="0.5"
          />
        </g>

        {/* Núcleo. */}
        <circle cx="300" cy="300" r="9" fill="currentColor" fillOpacity="0.5" />
      </svg>
    </div>
  );
}
