import Image from "next/image";

import { cn } from "@/lib/utils";

type Tone = "dark" | "light";

interface WorkLabMarkProps {
  className?: string;
  /** `dark` = ink oscuro sobre fondo claro; `light` = ink claro sobre fondo oscuro. */
  tone?: Tone;
  /** Etiqueta accesible; omítela cuando el isotipo acompaña al wordmark textual. */
  title?: string;
}

// Isotipo oficial (PNG hand-painted con alpha). Dimensiones intrínsecas reales
// por variante para que next/image reserve el aspecto correcto; el tamaño visible
// lo fija `className` (p. ej. size-8) con object-contain, sin deformar el trazo.
const ICON: Record<Tone, { src: string; w: number; h: number }> = {
  dark: { src: "/brand/worklab/icon_light.png", w: 505, h: 495 },
  light: { src: "/brand/worklab/icon_dark.png", w: 440, h: 425 },
};

/**
 * Isotipo WorkLab — emblema atómico oficial: la montaña roja del riesgo
 * rematada por un destello, orbitada por las elipses de un átomo.
 * WorkLab es una solución de HG Hurtado Gandini; hereda su rojo.
 */
export function WorkLabMark({ className, tone = "dark", title }: WorkLabMarkProps) {
  const icon = ICON[tone];
  return (
    <Image
      src={icon.src}
      alt={title ?? ""}
      width={icon.w}
      height={icon.h}
      aria-hidden={title ? undefined : true}
      className={cn("block object-contain", className)}
    />
  );
}
