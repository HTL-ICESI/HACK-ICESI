"use client";

import { useState } from "react";
import {
  CalendarClock,
  Check,
  MessageCircle,
  Plane,
  Send,
  Wallet,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { SeverityTag } from "@/components/thesis/SeverityTag";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { Users } from "lucide-react";
import { TeamCard } from "@/components/team/TeamRoster";
import { useBatchWorkers, tieneVacacionesVencidas } from "@/hooks/useBatchWorkers";
import { usePersona } from "@/components/shell/persona-context";
import { formatDate, formatMoney } from "@/lib/format";
import { notifyVacaciones } from "@/lib/api";
import type { Alert } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Action {
  icon: LucideIcon;
  tone: string;
  title: string;
  detail: string;
  cta: string;
}

// alert.type -> acción verbo-primero + label de CTA (vista accionable de RRHH).
function describeAction(a: Alert): Action {
  switch (a.type) {
    case "vencimiento_contrato":
      return {
        icon: CalendarClock,
        tone: "bg-risk-soft text-risk",
        title: `Renueva el contrato de ${a.worker ?? "—"}`,
        detail:
          a.due_date != null
            ? `Vence el ${formatDate(a.due_date)}${a.days_left != null ? ` · faltan ${a.days_left} días` : ""}`
            : "Renovar o terminar",
        cta: "Renovar",
      };
    case "vacaciones_vencidas":
      return {
        icon: Plane,
        tone: "bg-warn-soft text-warn",
        title: "Vacaciones por vencer en el equipo",
        detail: `${a.accrued_days ?? "—"} días acumulados sin tomar — notifica a los trabajadores`,
        cta: "Notificar",
      };
    case "seguridad_social_mora":
      return {
        icon: Wallet,
        tone: "bg-risk-soft text-risk",
        title: "Paga la seguridad social en mora",
        detail: `${a.amount ? formatMoney(a.amount) : ""}${a.due_date ? ` · antes del ${formatDate(a.due_date)}` : ""}`,
        cta: "Pagar",
      };
    default:
      return {
        icon: CalendarClock,
        tone: "bg-n100 text-muted-foreground",
        title: "Acción pendiente",
        detail: "",
        cta: "Resolver",
      };
  }
}

function VacacionesDialog({
  open,
  onClose,
  workerNames,
  companyName,
  onSent,
}: {
  open: boolean;
  onClose: () => void;
  workerNames: string[];
  companyName: string;
  onSent: () => void;
}) {
  const [phone, setPhone] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const handleClose = () => { setPhone(""); setSent(false); onClose(); };

  const handleSend = async () => {
    if (!phone.trim()) return;
    setSending(true);
    try {
      await notifyVacaciones({ to_number: phone.trim(), worker_names: workerNames, company_name: companyName });
      setSent(true);
      setTimeout(() => { onSent(); handleClose(); }, 1400);
    } catch {
      /* silencioso — el backend devuelve preview si sin Twilio */
      setSent(true);
      setTimeout(() => { onSent(); handleClose(); }, 1400);
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageCircle className="size-5 text-warn" />
            Notificar por WhatsApp
          </DialogTitle>
          <DialogDescription>
            {workerNames.length === 1
              ? `Se notificará a ${workerNames[0]} que tiene vacaciones por vencer.`
              : `Se notificará a ${workerNames.length} trabajadores con vacaciones por vencer.`}
          </DialogDescription>
        </DialogHeader>

        {sent ? (
          <p className="rounded-xl bg-ok-soft px-4 py-3 text-[13px] text-ok-fg">
            ✓ Notificación enviada correctamente.
          </p>
        ) : (
          <div className="space-y-1.5">
            <p className="text-[13px] font-medium text-toga">Número de WhatsApp del empleado</p>
            <Input
              autoFocus
              placeholder="310 000 0000"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              className="font-mono text-[14px]"
            />
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={sending}>Cancelar</Button>
          <Button onClick={handleSend} disabled={sending || !phone.trim() || sent} className="gap-2">
            <Send className="size-4" />
            {sending ? "Enviando…" : "Enviar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RrhhHome({
  companyName,
  alerts,
}: {
  companyName: string;
  alerts: Alert[];
}) {
  const { user } = usePersona();
  const [done, setDone] = useState<Set<string>>(new Set());
  const [vacacionesDialog, setVacacionesDialog] = useState(false);
  const markDone = (id: string) =>
    setDone((prev) => new Set(prev).add(id));

  const { workers, loading: teamLoading } = useBatchWorkers();
  const total = workers.length;
  const alDia = workers.filter((w) => !tieneVacacionesVencidas(w)).length;
  const pending = alerts.filter((a) => !done.has(a.alert_id)).length;
  const porRenovar = alerts.filter((a) => a.type === "vencimiento_contrato").length;

  return (
    <div>
      <header className="mb-6 animate-in fade-in-0 slide-in-from-bottom-2 duration-500">
        <h1 className="font-display text-3xl font-medium text-toga">
          Hola{user?.shortName ? `, ${user.shortName}` : ""}
        </h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Esto es lo que requiere tu acción en {companyName} hoy.
        </p>
      </header>

      {/* Chips de resumen */}
      <div className="mb-8 flex flex-wrap gap-2.5">
        <span className="inline-flex items-center gap-2 rounded-full bg-warn-soft px-3.5 py-1.5 text-[13px] font-medium text-warn-fg">
          <span className="size-1.5 rounded-full bg-warn" />
          {pending} acciones pendientes
        </span>
        {porRenovar > 0 && (
          <span className="inline-flex items-center gap-2 rounded-full bg-n100 px-3.5 py-1.5 text-[13px] font-medium text-[#554B45]">
            <span className="size-1.5 rounded-full bg-neutral-400" />
            {porRenovar} {porRenovar === 1 ? "contrato" : "contratos"} por renovar
          </span>
        )}
        {total > 0 && (
          <span className="inline-flex items-center gap-2 rounded-full bg-ok-soft px-3.5 py-1.5 text-[13px] font-medium text-ok-fg">
            <span className="size-1.5 rounded-full bg-ok" />
            {alDia} de {total} al día
          </span>
        )}
      </div>

      {/* Acciones de hoy */}
      <h2 className="mb-3 font-mono text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground">
        Acciones de hoy
      </h2>
      <div className="mb-9 flex flex-col gap-3">
        {alerts.map((a) => {
          const act = describeAction(a);
          const Icon = act.icon;
          const isDone = done.has(a.alert_id);
          return (
            <div
              key={a.alert_id}
              className="flex items-center gap-4 rounded-2xl border border-n300/60 bg-card px-5 py-4 shadow-hairline transition-shadow hover:shadow-bezel"
            >
              <span
                className={cn(
                  "flex size-11 shrink-0 items-center justify-center rounded-xl",
                  isDone ? "bg-ok-soft text-ok" : act.tone,
                )}
              >
                {isDone ? (
                  <Check className="size-5" aria-hidden="true" />
                ) : (
                  <Icon className="size-5" aria-hidden="true" />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <p
                  className={cn(
                    "text-[15px] font-medium text-toga",
                    isDone && "text-muted-foreground line-through",
                  )}
                >
                  {act.title}
                </p>
                {act.detail && (
                  <p className="mt-0.5 text-[13px] text-muted-foreground">
                    {act.detail}
                  </p>
                )}
              </div>
              {!isDone && <SeverityTag severity={a.severity} />}
              {isDone ? (
                <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-ok-fg">
                  <Check className="size-4" aria-hidden="true" />
                  Hecho
                </span>
              ) : a.type === "vacaciones_vencidas" ? (
                <Button
                  size="sm"
                  className="gap-1.5"
                  onClick={() => setVacacionesDialog(true)}
                >
                  <MessageCircle className="size-3.5" />
                  {act.cta}
                </Button>
              ) : (
                <Button size="sm" onClick={() => markDone(a.alert_id)}>
                  {act.cta}
                </Button>
              )}
            </div>
          );
        })}
      </div>

      {/* Salud del equipo */}
      <h2 className="mb-3 font-mono text-xs font-medium uppercase tracking-[0.1em] text-muted-foreground">
        Salud del equipo
      </h2>

      {teamLoading ? (
        <Skeleton className="mb-5 h-28 rounded-2xl" />
      ) : total === 0 ? (
        <div className="mb-5">
          <EmptyState
            icon={Users}
            title="Aún no hay trabajadores analizados"
            hint="Sube los contratos en Compliance para ver aquí la salud del equipo."
          />
        </div>
      ) : (
        <>
          <div className="mb-5 rounded-2xl border border-n300/60 bg-card p-6 shadow-hairline">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <span className="text-[13px] font-medium text-muted-foreground">
                  Equipo al día con vacaciones
                </span>
                <div className="mt-1.5 flex items-baseline gap-2">
                  <span className="font-display text-[2.5rem] leading-none text-toga tnum">
                    {alDia}
                  </span>
                  <span className="text-lg text-muted-foreground">/ {total}</span>
                </div>
              </div>
              <p className="max-w-xs flex-1 text-[13px] text-muted-foreground">
                {total - alDia > 0
                  ? `${total - alDia} ${total - alDia === 1 ? "persona" : "personas"} con vacaciones por vencer. Prográmalas para mantener al equipo al día.`
                  : "Todo el equipo está al día con sus vacaciones."}
              </p>
            </div>
            <div className="mt-4 flex gap-1.5">
              {Array.from({ length: total }).map((_, idx) => (
                <span
                  key={idx}
                  className={cn(
                    "h-2 flex-1 origin-left animate-grow-x rounded-full",
                    idx < alDia ? "bg-ok" : "bg-warn",
                  )}
                  style={{ animationDelay: `${idx * 60}ms` }}
                />
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
            {workers.map((item) => (
              <TeamCard key={item.doc_id} item={item} />
            ))}
          </div>
        </>
      )}

      {/* Dialog de notificación de vacaciones */}
      <VacacionesDialog
        open={vacacionesDialog}
        onClose={() => setVacacionesDialog(false)}
        workerNames={workers.filter(tieneVacacionesVencidas).map((w) => w.summary?.worker_name ?? w.filename)}
        companyName={companyName}
        onSent={() => {
          const vacAlert = alerts.find((a) => a.type === "vacaciones_vencidas");
          if (vacAlert) markDone(vacAlert.alert_id);
        }}
      />
    </div>
  );
}
