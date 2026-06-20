import { RotateCw, TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

/** Error inline con reintento. Evita el skeleton infinito o el vacío mudo. */
export function ErrorState({
  title = "No se pudo cargar",
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-n300/60 bg-card px-6 py-12 text-center shadow-hairline">
      <span className="flex size-11 items-center justify-center rounded-full bg-warn-soft text-warn">
        <TriangleAlert className="size-5" aria-hidden="true" />
      </span>
      <div>
        <p className="text-sm font-medium text-toga">{title}</p>
        {message && (
          <p className="mt-1 text-sm text-muted-foreground">{message}</p>
        )}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCw className="size-4" aria-hidden="true" />
          Reintentar
        </Button>
      )}
    </div>
  );
}
