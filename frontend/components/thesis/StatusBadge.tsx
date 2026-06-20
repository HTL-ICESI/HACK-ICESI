import { Check, FileText, Info, Lock, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Badge de estado del contrato (DESIGN.md §0, §4). El color ES el dato:
 * - calculado (verde): número determinista del backend.
 * - revisar (ámbar): texto redactado por el LLM ("borrador · revisar").
 * - needs_human (ámbar): el backend no pudo leer con confianza; nunca data inventada.
 * - bloqueado (rojo): `blocked: true` o nulidad pendiente; no se puede aprobar.
 * - info (cian): estado de lectura OCR, notas informativas.
 */
export type StatusKind =
  | "calculado"
  | "revisar"
  | "needs_human"
  | "bloqueado"
  | "info";

const MAP: Record<
  StatusKind,
  { cls: string; icon: LucideIcon; label: string }
> = {
  calculado: { cls: "badge-calculado", icon: Check, label: "calculado" },
  revisar: { cls: "badge-revisar", icon: FileText, label: "borrador · revisar" },
  needs_human: {
    cls: "badge-revision-humana",
    icon: TriangleAlert,
    label: "requiere revisión humana",
  },
  bloqueado: { cls: "badge-bloqueado", icon: Lock, label: "bloqueado" },
  info: { cls: "badge-info", icon: Info, label: "info" },
};

interface StatusBadgeProps {
  kind: StatusKind;
  /** Sobrescribe el texto por defecto. */
  label?: string;
  className?: string;
}

export function StatusBadge({ kind, label, className }: StatusBadgeProps) {
  const { cls, icon: Icon, label: defaultLabel } = MAP[kind];
  return (
    <span className={cn(cls, className)}>
      <Icon className="size-3" aria-hidden="true" />
      {label ?? defaultLabel}
    </span>
  );
}
