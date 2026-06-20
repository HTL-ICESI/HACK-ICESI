import type { Transition, Variants } from "motion/react";

/**
 * Tokens de movimiento HG (adaptados de patrones de cult-ui, re-tonalizados a la
 * sobriedad legal-lujo del manual). Una sola fuente para resortes y transiciones
 * de paneles/pills/contenido, alineada a las curvas de `tailwind.config.ts`:
 *   - fluid  = drawer iOS (alturas/paneles)
 *   - snappy = ease-out fuerte (entradas)
 * `prefers-reduced-motion` se respeta globalmente en `globals.css`; aun así,
 * los componentes que usan `motion/react` deben cortar la animación con
 * `useReducedMotion()` (motion no lee la media query por sí solo en layout).
 */

/** Curva "fluid" (cubic-bezier(0.32,0.72,0,1)) — alturas y drawers. */
export const easeFluid: [number, number, number, number] = [0.32, 0.72, 0, 1];

/** Curva "snappy" (cubic-bezier(0.23,1,0.32,1)) — entradas con punch contenido. */
export const easeSnappy: [number, number, number, number] = [0.23, 1, 0.32, 1];

/** Pill compartida (segmented control). Resorte muy contenido: nada de rebote. */
export const springPill: Transition = {
  type: "spring",
  bounce: 0.16,
  duration: 0.42,
};

/** Swap de vistas pares (contenido direccional). Resorte sobrio. */
export const springContent: Transition = {
  type: "spring",
  bounce: 0.14,
  duration: 0.44,
};

/** Expand/collapse de altura (acordeón, detalles). Tween drawer, sin rebote. */
export const panelTween: Transition = { duration: 0.32, ease: easeFluid };

/**
 * Slide direccional sobrio para intercambiar vistas pares (p. ej. el swap de
 * persona en el dashboard). 28px + desenfoque leve — nunca el "300px teatral"
 * de una librería de marketing. El contenido nuevo entra desde el lado +dir y el
 * anterior sale hacia -dir. Pasa `custom={dir}` a `AnimatePresence` y a la capa.
 */
export function directionalSlide(offset = 28): Variants {
  return {
    initial: (dir: number) => ({
      x: dir * offset,
      opacity: 0,
      filter: "blur(4px)",
    }),
    active: { x: 0, opacity: 1, filter: "blur(0px)" },
    exit: (dir: number) => ({
      x: dir * -offset,
      opacity: 0,
      filter: "blur(4px)",
    }),
  };
}

/** Variante de crossfade puro — fallback para reduced-motion. */
export const fadeOnly: Variants = {
  initial: { opacity: 0 },
  active: { opacity: 1 },
  exit: { opacity: 0 },
};
