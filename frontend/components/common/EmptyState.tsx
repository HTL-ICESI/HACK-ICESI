import type { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  hint?: string;
}

/** Estado vacío compuesto (no una lista en blanco que se ve rota). */
export function EmptyState({ icon: Icon, title, hint }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center">
      <span className="flex size-10 items-center justify-center rounded-full bg-ok-soft text-ok">
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <p className="text-sm font-medium text-toga">{title}</p>
      {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
    </div>
  );
}
