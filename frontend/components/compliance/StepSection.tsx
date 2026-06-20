import { Check, ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

interface StepSectionProps {
  n: number;
  title: string;
  done?: boolean;
  /** Badge a la derecha cuando el paso está EXPANDIDO. */
  badge?: React.ReactNode;
  /** "Recibo" compacto a la derecha cuando el paso está COLAPSADO. */
  summary?: React.ReactNode;
  /** Controla expandido/colapsado. Por defecto expandido (sin acordeón). */
  open?: boolean;
  /** Si se pasa, la cabecera es un botón que colapsa/expande el paso. */
  onToggle?: () => void;
  children: React.ReactNode;
}

/**
 * Paso del flujo de Compliance Vivo, como ítem de acordeón. Solo el paso activo
 * queda expandido; los completados se colapsan a un "recibo" de una línea con su
 * resultado clave (reabrible). Evita el scroll infinito del flujo multi-paso.
 * Los hijos traen su propia card: aquí no se envuelve nada (no anidar cards).
 */
export function StepSection({
  n,
  title,
  done,
  badge,
  summary,
  open = true,
  onToggle,
  children,
}: StepSectionProps) {
  const numberBadge = (
    <span
      className={cn(
        "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
        done ? "bg-toga text-lienzo" : "bg-acento-soft text-acento",
      )}
    >
      {done ? <Check className="size-4" aria-hidden="true" /> : n}
    </span>
  );

  const title_ = (
    <span className="font-display text-lg font-medium text-toga">{title}</span>
  );

  const rightSide = (
    <span className="ml-auto flex items-center gap-3">
      {open ? badge : (summary ?? badge)}
      {onToggle && (
        <ChevronDown
          className={cn(
            "size-4 shrink-0 text-muted-foreground transition-transform duration-200 ease-out",
            open && "rotate-180",
          )}
          aria-hidden="true"
        />
      )}
    </span>
  );

  return (
    <section className="animate-in fade-in-0 slide-in-from-bottom-3 duration-500">
      {onToggle ? (
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={open}
          className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-n100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acento focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          {numberBadge}
          {title_}
          {rightSide}
        </button>
      ) : (
        <div className="flex w-full items-center gap-3 px-2 py-2">
          {numberBadge}
          {title_}
          {rightSide}
        </div>
      )}

      {open && (
        <div className="ml-10 mt-3 animate-in fade-in-0 slide-in-from-top-1 duration-200">
          {children}
        </div>
      )}
    </section>
  );
}
