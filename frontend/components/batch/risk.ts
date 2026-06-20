import type { BatchItemSummary } from "@/lib/types";

export type RiskLevel = BatchItemSummary["risk_level"];

/** Tokens del semáforo por nivel de riesgo (DESIGN.md): alto=rojo, medio=ámbar, bajo=verde. */
export const RISK_STYLE: Record<RiskLevel, { dot: string; chip: string; label: string }> = {
  alto: { dot: "bg-risk", chip: "bg-risk-soft text-risk-fg", label: "Riesgo alto" },
  medio: { dot: "bg-warn", chip: "bg-warn-soft text-warn-fg", label: "Riesgo medio" },
  bajo: { dot: "bg-ok", chip: "bg-ok-soft text-ok-fg", label: "Riesgo bajo" },
};
