"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  CalendarClock,
  FileText,
  Loader2,
  MessageSquareText,
  Paperclip,
  Phone,
  Send,
  ShieldCheck,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  contrastDescargo,
  generateDisciplinaryDocs,
  getCallResult,
  sendEvidenceWhatsApp,
  startDescargosCall,
} from "@/lib/api";
import { INITIAL_DILIGENCE_STATE, evaluateGuardian } from "@/lib/guardian";
import type {
  DescargoContrast,
  DiligenceState,
  DisciplinaryDoc,
  EvidenceWhatsAppResult,
  StartCallResult,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { usePersona } from "@/components/shell/persona-context";
import type { DiligenceMeta } from "./DiligenceForm";
import { GuardianPanel } from "./GuardianPanel";

const SESSION = "desc-001";

// Transcripción del descargo que produce la llamada (en vivo llega del webhook /
// de la conversación de ElevenLabs; aquí, respaldo demo-safe si no hay credenciales).
const DEMO_DESCARGO =
  "El trabajador manifiesta que las ausencias de los días 4 y 5 obedecieron a una " +
  "incapacidad médica que no alcanzó a radicar a tiempo, y reconoce la inasistencia del " +
  "día 3. Solicita que se tengan en cuenta sus diez años de servicio sin sanciones previas.";

// Fecha de la llamada: 3 días hábiles después de hoy, 10:00 a.m. (regla del proceso).
function scheduledCall(): { iso: string; label: string } {
  const d = new Date();
  let added = 0;
  while (added < 3) {
    d.setDate(d.getDate() + 1);
    const day = d.getDay();
    if (day !== 0 && day !== 6) added += 1;
  }
  d.setHours(10, 0, 0, 0);
  const label = d.toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  return { iso: d.toISOString(), label };
}

function StepHeader({
  icon: Icon,
  n,
  title,
  done,
}: {
  icon: LucideIcon;
  n: number;
  title: string;
  done?: boolean;
}) {
  return (
    <div className="mb-3 flex items-center gap-3">
      <span
        className={cn(
          "flex size-7 shrink-0 items-center justify-center rounded-lg text-xs font-semibold",
          done ? "bg-ok text-white" : "bg-acento-soft text-acento",
        )}
      >
        {done ? "✓" : n}
      </span>
      <Icon className="size-4 text-muted-foreground" aria-hidden />
      <h2 className="font-display text-base font-medium text-toga">{title}</h2>
    </div>
  );
}

const COBERTURA_STYLE: Record<DescargoContrast["cobertura"], string> = {
  total: "bg-ok-soft text-ok-fg",
  parcial: "bg-warn-soft text-warn-fg",
  nula: "bg-risk-soft text-risk-fg",
  no_evaluado: "bg-n100 text-muted-foreground",
};

export function DescargosPipeline({
  meta,
  companyName,
  telefono,
  onTelefono,
}: {
  meta: DiligenceMeta;
  companyName: string;
  telefono: string;
  onTelefono?: (phone: string) => void;
}) {
  const call = useMemo(scheduledCall, []);
  const { user } = usePersona(); // el abogado en sesión: firma docs + va en el WhatsApp

  // Celular registrado del trabajador (viene de su ficha). Editable, no se pregunta.
  const [phone, setPhone] = useState(telefono);
  const [editPhone, setEditPhone] = useState(false);

  // Evidencia (nombres). El cuerpo del WhatsApp las lista; subirlas al expediente es J1.
  const [evidence, setEvidence] = useState<string[]>([]);

  // Estado del debido proceso (lo que el Guardián vigila en vivo).
  const [state, setState] = useState<DiligenceState>(INITIAL_DILIGENCE_STATE);
  const guardian = evaluateGuardian(SESSION, state);
  const toggle = (k: keyof DiligenceState) =>
    setState((p) => ({ ...p, [k]: !p[k] }));

  // Paso 1 — WhatsApp
  const [wa, setWa] = useState<EvidenceWhatsAppResult | null>(null);
  const [waLoading, setWaLoading] = useState(false);

  // Paso 2 — Llamada
  const [callRes, setCallRes] = useState<StartCallResult | null>(null);
  const [callErr, setCallErr] = useState<string | null>(null);
  const [callLoading, setCallLoading] = useState(false);
  const [waiting, setWaiting] = useState(false); // esperando la transcripción real
  const [isDemo, setIsDemo] = useState(false); // descargo de respaldo (sin telefonía)
  const pollRef = useRef(false);

  // Detiene el polling al desmontar.
  useEffect(() => () => { pollRef.current = false; }, []);

  // Paso 3 — Descargo + contraste
  const [descargo, setDescargo] = useState("");
  const [contrast, setContrast] = useState<DescargoContrast | null>(null);
  const [contrastLoading, setContrastLoading] = useState(false);

  // Paso 4 — Documentos (J4)
  const [docs, setDocs] = useState<DisciplinaryDoc[] | null>(null);
  const [docsLoading, setDocsLoading] = useState(false);

  async function sendWhatsApp() {
    setWaLoading(true);
    try {
      const res = await sendEvidenceWhatsApp({
        to_number: phone,
        worker_name: meta.worker,
        company_name: companyName,
        charges_summary: meta.falta,
        evidence_names: evidence,
        call_date: call.label,
        lawyer_name: user?.name ?? "",
      });
      setWa(res);
    } catch (e) {
      setWa({
        to: phone,
        body: "",
        media: [],
        configured: false,
        sent: false,
        error: e instanceof Error ? e.message : "Error de red",
      });
    } finally {
      setWaLoading(false);
    }
  }

  async function placeCall() {
    setCallLoading(true);
    setCallErr(null);
    try {
      const res = await startDescargosCall({
        session_id: SESSION,
        to_number: phone,
        company_name: companyName,
        worker_name: meta.worker,
        charges_summary: meta.falta,
        evidence_summary: evidence.join("; "),
        citation_date: new Date().toLocaleDateString("es-CO"),
        diligence_date: call.label,
        defense_term_elapsed: "cinco (5) días hábiles",
      });
      setCallRes(res);
      if (res.conversation_id) {
        // Llamada real en curso → espera la transcripción que genere ElevenLabs.
        setWaiting(true);
        pollTranscript(res.conversation_id);
      } else {
        setDescargo(DEMO_DESCARGO);
        setIsDemo(true);
      }
    } catch (e) {
      // Sin credenciales de telefonía → respaldo de demostración (claramente marcado).
      setCallErr(e instanceof Error ? e.message : "La telefonía no está disponible.");
      setDescargo(DEMO_DESCARGO);
      setIsDemo(true);
    } finally {
      setCallLoading(false);
    }
  }

  // Polling de la transcripción real (patrón AFFIRMA: fetch_conversation post-llamada).
  async function pollTranscript(cid: string) {
    pollRef.current = true;
    for (let attempt = 0; attempt < 40 && pollRef.current; attempt++) {
      try {
        const r = await getCallResult(cid);
        if (r.descargo && r.descargo.trim().length > 0) {
          setDescargo(r.descargo);
          setIsDemo(false);
          setWaiting(false);
          return;
        }
      } catch {
        // Aún no termina la llamada o no hay credenciales — se reintenta.
      }
      await new Promise((res) => setTimeout(res, 5000));
    }
    setWaiting(false);
  }

  async function runContrast() {
    setContrastLoading(true);
    try {
      const res = await contrastDescargo({
        charges_summary: meta.falta,
        evidence_summary: evidence.join("; "),
        descargo_text: descargo,
      });
      setContrast(res);
      // El descargo se rindió → marca la garantía en el Guardián.
      setState((p) => ({ ...p, worker_allowed_to_respond: true }));
    } finally {
      setContrastLoading(false);
    }
  }

  async function genDocs() {
    setDocsLoading(true);
    try {
      const res = await generateDisciplinaryDocs(
        SESSION, state, descargo || meta.falta, user?.name ?? "",
      );
      setDocs(res.documents);
    } finally {
      setDocsLoading(false);
    }
  }

  const card = "rounded-2xl border border-n300/60 bg-card p-5 shadow-hairline";

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* Guardián fijo a la derecha */}
      <aside className="lg:order-2 lg:col-span-1">
        <div className="lg:sticky lg:top-24">
          <div className="rounded-2xl border border-n300/60 bg-card p-5 shadow-bezel">
            <div className="mb-4 flex items-center gap-3">
              <span className="flex size-8 items-center justify-center rounded-lg bg-toga text-lienzo">
                <ShieldCheck className="size-4" aria-hidden />
              </span>
              <h2 className="font-display text-base font-medium text-toga">
                Guardián del debido proceso
              </h2>
              <span className="ml-auto">
                {guardian.nullity_alert ? (
                  <span className="badge-bloqueado">riesgo de nulidad</span>
                ) : (
                  <span className="badge-calculado">✓ sin nulidades</span>
                )}
              </span>
            </div>
            <GuardianPanel state={state} onToggle={toggle} />
          </div>
        </div>
      </aside>

      {/* Pipeline a la izquierda */}
      <div className="space-y-5 lg:order-1 lg:col-span-2">
        {/* Contacto del trabajador — viene de su ficha, no se pregunta */}
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-n300/60 bg-n100/40 px-4 py-2.5 text-sm">
          <Phone className="size-4 text-muted-foreground" aria-hidden />
          <span className="text-muted-foreground">WhatsApp del trabajador (ficha):</span>
          {editPhone ? (
            <input
              autoFocus
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              onBlur={() => {
                setEditPhone(false);
                onTelefono?.(phone);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setEditPhone(false);
                  onTelefono?.(phone);
                }
              }}
              className="rounded border border-n300 bg-card px-2 py-0.5 font-mono text-[13px] text-toga focus:outline-none focus:ring-2 focus:ring-acento"
            />
          ) : (
            <span className="font-mono font-medium text-toga">{phone}</span>
          )}
          <button
            type="button"
            onClick={() => setEditPhone((v) => !v)}
            className="ml-auto rounded px-1.5 py-0.5 text-xs font-medium text-acento hover:bg-acento-soft"
          >
            {editPhone ? "Guardar" : "Editar"}
          </button>
        </div>

        {/* Paso 1 — Evidencia + WhatsApp */}
        <section className={card}>
          <StepHeader icon={Send} n={1} title="Evidencia y citación por WhatsApp" done={Boolean(wa?.sent || wa?.preview)} />
          <EvidencePicker evidence={evidence} onChange={setEvidence} />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button onClick={sendWhatsApp} disabled={waLoading || !phone}>
              {waLoading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              Enviar evidencia + citación
            </Button>
            <span className="text-xs text-muted-foreground">
              al WhatsApp {phone || "— (falta el número)"}
            </span>
          </div>
          {wa && (
            <div className="mt-3 rounded-lg border border-n300/60 bg-n100/50 p-3">
              <p className="mb-1.5 flex items-center gap-2 text-xs font-medium">
                {wa.sent ? (
                  <span className="text-ok-fg">✓ Enviado a {wa.to}</span>
                ) : wa.error ? (
                  <span className="text-risk-fg">No se pudo enviar: {wa.error}</span>
                ) : (
                  <span className="text-warn-fg">
                    Vista previa — se enviará al conectar Twilio
                  </span>
                )}
              </p>
              {wa.body && (
                <p className="whitespace-pre-wrap text-[12px] leading-relaxed text-[#554B45]">
                  {wa.body}
                </p>
              )}
            </div>
          )}
        </section>

        {/* Paso 2 — Llamada de descargos */}
        <section className={card}>
          <StepHeader icon={Phone} n={2} title="Llamada de descargos" done={Boolean(callRes)} />
          <div className="flex items-start gap-3 rounded-lg bg-acento-soft/40 px-3.5 py-2.5">
            <CalendarClock className="mt-0.5 size-4 shrink-0 text-acento" aria-hidden />
            <p className="text-sm text-toga">
              Programada para el <span className="font-medium capitalize">{call.label}</span> a las{" "}
              <span className="font-medium">10:00 a.m.</span> — la llamada se graba y el agente
              conduce la diligencia.
            </p>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button onClick={placeCall} disabled={callLoading || !phone}>
              {callLoading ? <Loader2 className="size-4 animate-spin" /> : <Phone className="size-4" />}
              Llamar ahora
            </Button>
            {callRes && (
              <span className="text-xs text-ok-fg">
                ✓ Llamada iniciada{callRes.conversation_id ? ` · conv ${callRes.conversation_id.slice(0, 8)}…` : ""}
              </span>
            )}
            {callErr && <span className="text-xs text-warn-fg">{callErr}</span>}
          </div>
        </section>

        {/* Paso 3 — Descargo + contraste */}
        <section className={card}>
          <StepHeader icon={MessageSquareText} n={3} title="Descargo del trabajador" done={Boolean(contrast)} />
          {descargo ? (
            <div className="space-y-1.5">
              <Textarea
                value={descargo}
                readOnly
                className="min-h-[96px] cursor-default bg-n100/50"
              />
              <p className="text-[11px] text-muted-foreground">
                {isDemo
                  ? "Transcripción de demostración (sin telefonía conectada)."
                  : "Transcripción tomada de la llamada (ElevenLabs)."}
              </p>
            </div>
          ) : waiting ? (
            <p className="flex items-center gap-2 rounded-lg border border-dashed border-acento/40 bg-acento/5 px-3.5 py-3 text-sm text-acento">
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Esperando los descargos de la llamada…
            </p>
          ) : (
            <p className="rounded-lg border border-dashed border-n300 bg-n100/40 px-3.5 py-3 text-sm text-muted-foreground">
              La transcripción del descargo aparecerá aquí cuando se realice la llamada.
            </p>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button
              variant="secondary"
              onClick={runContrast}
              disabled={contrastLoading || descargo.trim().length < 10}
            >
              {contrastLoading && <Loader2 className="size-4 animate-spin" />}
              Contrastar con los cargos
            </Button>
          </div>
          {contrast && (
            <div className="mt-3 space-y-2 rounded-lg border border-n300/60 bg-n100/50 p-3">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize",
                    COBERTURA_STYLE[contrast.cobertura],
                  )}
                >
                  cobertura: {contrast.cobertura.replace("_", " ")}
                </span>
                {contrast.evaluado_por === "sin_llm" && (
                  <span className="text-[11px] text-muted-foreground">revisión manual</span>
                )}
              </div>
              <p className="text-[13px] text-toga">{contrast.resumen}</p>
              {contrast.puntos_sin_responder?.length > 0 && (
                <p className="text-[12px] text-risk-fg">
                  Sin responder: {contrast.puntos_sin_responder.join("; ")}
                </p>
              )}
            </div>
          )}
        </section>

        {/* Paso 4 — Documento final (J4) */}
        <section className={card}>
          <StepHeader icon={FileText} n={4} title="Documentos del proceso" done={Boolean(docs)} />
          {!docs ? (
            <>
              <Button onClick={genDocs} disabled={docsLoading || !descargo.trim()}>
                {docsLoading ? <Loader2 className="size-4 animate-spin" /> : <FileText className="size-4" />}
                Generar documentos
              </Button>
              {!descargo.trim() ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Disponible cuando se realice la llamada y se tomen los descargos del trabajador.
                </p>
              ) : (
                !guardian.can_proceed && (
                  <p className="mt-2 text-xs text-warn-fg">
                    La decisión final saldrá bloqueada hasta cerrar los pasos críticos del Guardián.
                  </p>
                )
              )}
            </>
          ) : (
            <ul className="space-y-2">
              {docs.map((d) => (
                <li
                  key={d.type}
                  className="flex items-center gap-2 rounded-lg border border-n300/60 bg-card px-3.5 py-2.5"
                >
                  <FileText className="size-4 text-acento" aria-hidden />
                  <span className="flex-1 text-sm font-medium text-toga">{d.title}</span>
                  {d.blocked_if_nullity && !guardian.can_proceed && (
                    <span className="badge-bloqueado">bloqueado</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function EvidencePicker({
  evidence,
  onChange,
}: {
  evidence: string[];
  onChange: (v: string[]) => void;
}) {
  return (
    <div className="space-y-2">
      <label className="flex w-fit cursor-pointer items-center gap-2 rounded-lg border border-dashed border-n300 bg-n100/40 px-3.5 py-2 text-sm font-medium text-toga transition-colors hover:border-acento/40 hover:bg-acento/5">
        <Paperclip className="size-4" aria-hidden />
        Adjuntar evidencia
        <input
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            const names = Array.from(e.target.files ?? []).map((f) => f.name);
            if (names.length) onChange([...evidence, ...names]);
            e.currentTarget.value = "";
          }}
        />
      </label>
      {evidence.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {evidence.map((name, i) => (
            <span
              key={`${name}-${i}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-n300/60 bg-card px-2.5 py-1 text-[12px] text-toga"
            >
              {name}
              <button
                type="button"
                onClick={() => onChange(evidence.filter((_, j) => j !== i))}
                className="text-muted-foreground hover:text-risk-fg"
                aria-label={`Quitar ${name}`}
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
