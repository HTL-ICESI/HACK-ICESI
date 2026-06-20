import { ArrowRight } from "lucide-react";

import { SeverityTag } from "@/components/thesis/SeverityTag";
import { SourceChip } from "@/components/thesis/SourceChip";
import type { Gap, RemedyType } from "@/lib/types";

const REMEDY_LABEL: Record<RemedyType, string> = {
  otrosi: "Otrosí",
  contrato_corregido: "Contrato corregido",
  instruccion_nomina: "Instrucción a nómina",
  acta_terminacion: "Acta de terminación",
};

function isReclasificacion(gap: Gap): boolean {
  return (
    gap.citation.norm_id === "Ley 2466" ||
    gap.remedy_type === "contrato_corregido"
  );
}

export function GapsList({ gaps }: { gaps: Gap[] }) {
  return (
    <div className="space-y-3">
      {gaps.map((gap) => (
        <div
          key={gap.gap_id}
          className="rounded-lg border border-n300/60 bg-card p-4 shadow-hairline"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-medium text-toga">{gap.issue}</p>
            <SeverityTag severity={gap.severity} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <SourceChip citation={gap.citation} source={gap.source} />
            {isReclasificacion(gap) && (
              <span className="badge-revisar">riesgo de reclasificación</span>
            )}
            <span className="ml-auto inline-flex items-center gap-1 text-xs text-muted-foreground">
              <ArrowRight className="size-3" aria-hidden="true" />
              {REMEDY_LABEL[gap.remedy_type]}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
