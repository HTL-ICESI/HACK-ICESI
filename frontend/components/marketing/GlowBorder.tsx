import { cn } from "@/lib/utils";

interface GlowBorderProps {
  children: React.ReactNode;
  /** Wrapper externo (tamaño, sombra, hover). */
  className?: string;
  /** Panel de contenido (fondo, padding). */
  innerClassName?: string;
  /** Utilidad de redondeo; debe coincidir dentro/fuera. */
  radius?: string;
}

/**
 * Borde con luz roja HG que gira (micro-componente de marca, estilo uiverse
 * re-tonalizado). SOLO landing. Un haz cónico rojo recorre el borde sobre una
 * línea tenue de base; el panel de contenido enmascara el centro.
 * `motion-reduce`: la luz se congela (queda un borde con gradiente estático).
 */
export function GlowBorder({
  children,
  className,
  innerClassName,
  radius = "rounded-2xl",
}: GlowBorderProps) {
  return (
    <div className={cn("relative isolate overflow-hidden p-px", radius, className)}>
      <span
        aria-hidden="true"
        className="pointer-events-none absolute inset-[-150%] -z-10 animate-[spin_7s_linear_infinite] bg-[conic-gradient(from_0deg,transparent_0deg,transparent_58deg,#E07A72_82deg,#801817_102deg,transparent_138deg,transparent_360deg)] motion-reduce:animate-none"
      />
      <span
        aria-hidden="true"
        className={cn(
          "pointer-events-none absolute inset-0 -z-10 border border-white/12",
          radius,
        )}
      />
      <div className={cn(radius, innerClassName)}>{children}</div>
    </div>
  );
}
