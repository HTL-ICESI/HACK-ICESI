import type { LucideIcon } from "lucide-react";

/**
 * Placeholder de pantalla aún no construida. Mantiene el shell navegable y
 * en marca mientras se levantan las vistas reales en sus fases.
 */
interface PhasePlaceholderProps {
  screenId: string;
  title: string;
  description: string;
  phase: string;
  icon: LucideIcon;
}

export function PhasePlaceholder({
  screenId,
  title,
  description,
  phase,
  icon: Icon,
}: PhasePlaceholderProps) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <div className="rounded-2xl border border-n300/60 bg-card p-8 shadow-bezel md:p-10">
        <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-acento">
          {screenId}
        </span>
        <div className="mt-4 flex items-center gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-acento-soft text-acento">
            <Icon className="size-6" aria-hidden="true" />
          </span>
          <h1 className="font-display text-3xl font-medium text-toga">
            {title}
          </h1>
        </div>
        <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-[#554B45]">
          {description}
        </p>
        <div className="mt-6">
          <span className="badge-info">{phase}</span>
        </div>
      </div>
    </div>
  );
}
