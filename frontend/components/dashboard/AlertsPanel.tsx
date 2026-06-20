import { ArrowRight, Bell, CalendarClock, CheckCircle2, Plane, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/EmptyState";
import { SeverityTag } from "@/components/thesis/SeverityTag";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate, formatMoney } from "@/lib/format";
import type { Alert } from "@/lib/types";
import { cn } from "@/lib/utils";

// Mapea tipo de alerta → gap_id del motor de compliance (para filtrar el batch).
const ALERT_TO_GAP: Record<string, string> = {
  vacaciones_vencidas: "g3",
  vencimiento_contrato: "g4",
  seguridad_social_mora: "g5",
};

interface Described {
  icon: LucideIcon;
  text: string;
  meta: string;
}

// Texto accionable: verbo + fecha + consecuencia (sin jerga, sirve a Abogado y RRHH).
function describe(a: Alert): Described {
  switch (a.type) {
    case "vencimiento_contrato":
      return {
        icon: CalendarClock,
        text: `Contrato de ${a.worker ?? "—"} vence el ${
          a.due_date ? formatDate(a.due_date) : "—"
        }`,
        meta:
          a.days_left != null
            ? `Faltan ${a.days_left} días — renovar o terminar`
            : "Renovar o terminar",
      };
    case "vacaciones_vencidas":
      return {
        icon: Plane,
        text: `Vacaciones acumuladas: ${a.accrued_days ?? "—"} días`,
        meta: "Programar antes de que sigan venciendo",
      };
    case "seguridad_social_mora":
      return {
        icon: Wallet,
        text: `Seguridad social en mora${
          a.amount ? ` — ${formatMoney(a.amount)}` : ""
        }`,
        meta: a.due_date
          ? `Pagar antes del ${formatDate(a.due_date)}`
          : "Pagar cuanto antes",
      };
    default:
      return { icon: Bell, text: "Alerta", meta: "" };
  }
}

const ICON_TONE: Record<Alert["severity"], string> = {
  alta: "bg-risk-soft text-risk",
  media: "bg-warn-soft text-warn",
  baja: "bg-n100 text-muted-foreground",
};

// Lo más urgente primero (alta -> media -> baja), como pide la vista accionable.
const SEVERITY_RANK: Record<Alert["severity"], number> = {
  alta: 0,
  media: 1,
  baja: 2,
};

interface AlertsPanelProps {
  alerts: Alert[];
  className?: string;
}

export function AlertsPanel({ alerts, className }: AlertsPanelProps) {
  const ordered = [...alerts].sort(
    (a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity],
  );
  return (
    <Card className={cn("border-n300/60 shadow-hairline", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-toga">Alertas</h2>
          <span className="font-mono text-xs text-muted-foreground tnum">
            {alerts.length}
          </span>
        </div>

        {alerts.length === 0 ? (
          <EmptyState
            icon={CheckCircle2}
            title="Sin alertas pendientes"
            hint="Todo al día en esta empresa."
          />
        ) : (
          <ul className="mt-4 divide-y divide-n300/50">
            {ordered.map((a) => {
              const { icon: Icon, text, meta } = describe(a);
              const gap = ALERT_TO_GAP[a.type];
              const href = gap ? `/batch?gap=${gap}` : "/batch";
              return (
                <li key={a.alert_id}>
                  <Link
                    href={href}
                    className="group flex items-start gap-3 py-3 first:pt-0 last:pb-0 hover:bg-n100/50 -mx-6 px-6 transition-colors rounded-lg"
                  >
                    <span
                      className={cn(
                        "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg",
                        ICON_TONE[a.severity],
                      )}
                    >
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-toga">{text}</p>
                      <p className="text-sm text-muted-foreground">{meta}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <SeverityTag severity={a.severity} />
                      <ArrowRight className="size-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden />
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
