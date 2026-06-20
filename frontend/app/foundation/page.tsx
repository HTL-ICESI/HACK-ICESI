import { Logo } from "@/components/brand/Logo";
import { Money } from "@/components/thesis/Money";
import { SeverityTag } from "@/components/thesis/SeverityTag";
import { SourceChip } from "@/components/thesis/SourceChip";
import { StatusBadge } from "@/components/thesis/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { mockCompliance, mockExposure, mockExtract } from "@/lib/mocks";

/**
 * PREVIEW DE FUNDACIÓN (/foundation) — smoke test visual del sistema de diseño:
 * tokens, fuentes y primitivos de la tesis. No es una pantalla del producto.
 */
export default function FoundationPreview() {
  const magic = mockExposure.magic_number;
  const salary = mockExtract.record.base_salary;
  const gap = mockCompliance.gaps[0];

  return (
    <TooltipProvider delayDuration={150} skipDelayDuration={0}>
      <main className="mx-auto max-w-5xl space-y-12 px-6 py-16">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <Logo />
          <span className="rounded-full bg-acento-soft px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-acento">
            Fundación · sistema de diseño
          </span>
        </header>

        <div className="flex items-center gap-4 rounded-lg bg-toga p-6 shadow-bezel">
          <Logo tone="light" />
          <span className="ml-auto font-mono text-[11px] text-lienzo/60">
            negativo · sidebar
          </span>
        </div>

        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Money shot
          </h2>
          <Card className="max-w-md shadow-bezel">
            <CardContent className="space-y-3 p-8">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Exposición en riesgo
                </span>
                <StatusBadge kind="calculado" />
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="cursor-help font-display text-money leading-none text-toga">
                    <Money value={magic.cop_exposure} className="font-display" />
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <span className="font-mono">{magic.exposure_formula}</span>
                </TooltipContent>
              </Tooltip>
              <p className="text-sm text-muted-foreground">
                {magic.outdated_clauses} cláusulas desactualizadas ·{" "}
                {magic.pct_outdated}%
              </p>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-8 md:grid-cols-2">
          <div className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Badges de estado
            </h2>
            <div className="flex flex-wrap gap-2">
              <StatusBadge kind="calculado" />
              <StatusBadge kind="revisar" />
              <StatusBadge kind="needs_human" />
              <StatusBadge kind="bloqueado" />
              <StatusBadge kind="info" label="OCR" />
            </div>
            <h2 className="pt-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Severidad
            </h2>
            <div className="flex flex-wrap gap-2">
              <SeverityTag severity="alta" />
              <SeverityTag severity="media" />
              <SeverityTag severity="baja" />
            </div>
          </div>

          <div className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Chip de fuente (clic para abrir la cita)
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted-foreground">Salario base</span>
              <Money value={salary.value.value} />
              <StatusBadge kind="calculado" />
              <SourceChip source={salary.source} label="contrato" />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm text-muted-foreground">
                Riesgo detectado
              </span>
              <SeverityTag severity={gap.severity} />
              <SourceChip citation={gap.citation} source={gap.source} />
            </div>
            <div className="flex gap-2 pt-2">
              <Button>Validar y aprobar</Button>
              <Button variant="outline">Ver fuentes</Button>
            </div>
          </div>
        </section>
      </main>
    </TooltipProvider>
  );
}
