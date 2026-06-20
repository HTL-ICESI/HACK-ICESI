"use client";

import { CheckCircle2, Circle, OctagonAlert } from "lucide-react";

import { SourceChip } from "@/components/thesis/SourceChip";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CHECKLIST, evaluateGuardian } from "@/lib/guardian";
import type { DiligenceState } from "@/lib/types";
import { cn } from "@/lib/utils";

interface GuardianPanelProps {
  state: DiligenceState;
  onToggle: (key: keyof DiligenceState) => void;
}

export function GuardianPanel({ state, onToggle }: GuardianPanelProps) {
  const result = evaluateGuardian("desc-001", state);
  const criticalMissing = CHECKLIST.filter(
    (rule) => rule.critical && !state[rule.key],
  );

  return (
    <div className="space-y-3">
      {/* Banner de nulidad — el único elemento que puede dominar (DESIGN.md §4). */}
      {result.nullity_alert && (
        <div className="animate-in fade-in-0 slide-in-from-top-2 duration-300">
          <Alert variant="nullity" className="animate-soft-pulse [&>svg]:size-4 [&>svg]:top-3 gap-x-2.5 px-3 py-2.5">
            <OctagonAlert />
            <AlertTitle className="font-display text-[13px]">
              Riesgo de nulidad
            </AlertTitle>
            <AlertDescription className="text-xs">
              {criticalMissing.map((rule) => (
                <div key={rule.key} className="mt-1.5 first:mt-0.5">
                  <p>
                    Falta: <strong>{rule.label}</strong>
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <SourceChip citation={rule.step.citation} />
                    <span className="text-[11px]">{rule.step.consequence}</span>
                  </div>
                </div>
              ))}
            </AlertDescription>
          </Alert>
        </div>
      )}

      {/* Checklist en vivo */}
      <div className="space-y-1.5">
        {CHECKLIST.map((rule) => {
          const done = state[rule.key];
          return (
            <button
              key={rule.key}
              type="button"
              role="checkbox"
              aria-checked={done}
              onClick={() => onToggle(rule.key)}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left transition-[background-color,transform] duration-150 active:scale-[0.99]",
                done
                  ? "border-ok/30 bg-ok-soft"
                  : rule.critical
                    ? "border-risk/30 bg-risk-soft"
                    : "border-n300/60 bg-card hover:bg-n100",
              )}
            >
              {done ? (
                <CheckCircle2 className="size-4 shrink-0 text-ok" />
              ) : (
                <Circle
                  className={cn(
                    "size-4 shrink-0",
                    rule.critical ? "text-risk" : "text-muted-foreground",
                  )}
                />
              )}
              <span className="flex-1 text-[13px] font-medium leading-snug text-toga">
                {rule.label}
              </span>
              {!done && rule.critical && (
                <span className="size-1.5 shrink-0 rounded-full bg-risk" aria-label="crítico" />
              )}
            </button>
          );
        })}
      </div>

      {/* Estado del Guardián */}
      <div
        role="status"
        aria-live="polite"
        className={cn(
          "rounded-lg px-3 py-2 text-[12px] font-medium leading-snug",
          result.can_proceed
            ? "bg-ok-soft text-ok-fg"
            : "bg-warn-soft text-warn-fg",
        )}
      >
        {result.can_proceed
          ? "Sin nulidades pendientes — la decisión se puede emitir."
          : "Pasos críticos pendientes — la decisión queda bloqueada."}
      </div>
    </div>
  );
}
