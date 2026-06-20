import { Check, ClipboardList, FileText, Gavel, Lock } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { DisciplinaryDoc, DisciplinaryDocType } from "@/lib/types";
import { cn } from "@/lib/utils";

const META: Record<DisciplinaryDocType, { icon: LucideIcon; label: string }> = {
  citacion_descargos: { icon: ClipboardList, label: "Citación a descargos" },
  acta_descargos: { icon: FileText, label: "Acta de descargos" },
  decision_final: { icon: Gavel, label: "Decisión final" },
};

interface DocumentsPanelProps {
  docs: DisciplinaryDoc[];
  canProceed: boolean;
}

export function DocumentsPanel({ docs, canProceed }: DocumentsPanelProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {docs.map((doc) => {
        const meta = META[doc.type];
        const Icon = meta.icon;
        const gated = Boolean(doc.blocked_if_nullity);
        const blocked = gated && !canProceed;
        // El documento bloqueado que acaba de desbloquearse: refuerza el "se desbloqueó".
        const ready = gated && canProceed;

        return (
          <div
            key={doc.type}
            className={cn(
              "rounded-xl border p-4 shadow-hairline transition-colors",
              blocked && "border-risk/30 bg-risk-soft",
              ready &&
                "animate-in fade-in-0 slide-in-from-bottom-1 border-acento/40 bg-card duration-300",
              !blocked && !ready && "border-n300/60 bg-card",
            )}
          >
            <Icon
              className={cn(
                "size-5",
                blocked ? "text-risk" : "text-acento",
              )}
              aria-hidden="true"
            />
            <p className="mt-3 text-sm font-medium text-toga">{meta.label}</p>

            {blocked ? (
              <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-risk-fg">
                <Lock className="size-3 shrink-0" />
                Bloqueada por nulidad pendiente
              </p>
            ) : ready ? (
              <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-ok-fg">
                <Check className="size-3.5 shrink-0" />
                Lista para emitir
              </p>
            ) : (
              <p className="mt-2 text-xs text-muted-foreground">
                Lista para revisar
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
