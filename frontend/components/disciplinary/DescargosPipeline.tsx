"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  CalendarClock,
  Download,
  Eye,
  FileText,
  Loader2,
  Lock,
  MessageSquareText,
  Paperclip,
  Phone,
  Send,
  ShieldCheck,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { marked } from "marked";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { downloadAsWord, downloadAsPdf } from "@/lib/docExport";
import {
  contrastDescargo,
  createExpediente,
  generateDisciplinaryDocs,
  getCallResult,
  sendDocumentWhatsApp,
  sendEvidenceWhatsApp,
  startDescargosCall,
  uploadDisciplinaryEvidence,
} from "@/lib/api";
import { INITIAL_DILIGENCE_STATE, evaluateGuardian } from "@/lib/guardian";
import type {
  CallTurn,
  DescargoContrast,
  DiligenceState,
  DisciplinaryDoc,
  DisciplinaryDocType,
  EvidenceWhatsAppResult,
  StartCallResult,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { usePersona } from "@/components/shell/persona-context";
import type { DiligenceMeta } from "./DiligenceForm";
import { GuardianPanel } from "./GuardianPanel";

const SESSION = "desc-001";

// Lo que dijo el trabajador en la conversación (fallback de descargo para el contraste).
function workerSpeech(turns?: CallTurn[]): string {
  return (turns ?? [])
    .filter((t) => t.role === "trabajador")
    .map((t) => t.message)
    .join(" ")
    .trim();
}

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

  // Evidencia: archivos REALES (bytes) para que Twilio los adjunte al WhatsApp.
  const [evidenceFiles, setEvidenceFiles] = useState<File[]>([]);
  const evidence = useMemo(() => evidenceFiles.map((f) => f.name), [evidenceFiles]);
  // process_id del expediente — se crea al subir la evidencia (lazy).
  const processIdRef = useRef<string | null>(null);

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
  const [turns, setTurns] = useState<CallTurn[]>([]); // conversación completa (agente/trabajador)
  const pollRef = useRef(false);

  // Detiene el polling al desmontar.
  useEffect(() => () => { pollRef.current = false; }, []);

  // Paso 3 — Descargo + contraste
  const [descargo, setDescargo] = useState("");
  const [contrast, setContrast] = useState<DescargoContrast | null>(null);
  const [contrastLoading, setContrastLoading] = useState(false);

  // Paso 4 — Documentos (J4) — progresivos: citación al inicio, acta tras descargos,
  // decisión final desbloqueada cuando existen las dos primeras.
  const [citacionDoc, setCitacionDoc] = useState<DisciplinaryDoc | null>(null);
  const [actaDoc, setActaDoc] = useState<DisciplinaryDoc | null>(null);
  const [decisionDoc, setDecisionDoc] = useState<DisciplinaryDoc | null>(null);
  const [genLoading, setGenLoading] = useState<string | null>(null);     // tipo en generación
  const [genError, setGenError] = useState<string | null>(null);         // tipo que falló al generar
  const [docWaSending, setDocWaSending] = useState<string | null>(null); // tipo enviándose por WA
  const [docWaResult, setDocWaResult] = useState<{ type: string; ok: boolean; note?: string } | null>(null);

  // ── Persistencia: el proceso sobrevive a navegar entre pestañas ────────────
  // Todo el avance (transcripción, descargo, documentos, guardián) se guarda por
  // trabajador en localStorage y se rehidrata al volver. Antes se perdía al salir.
  const storageKey = `descargos:${meta.doc_id || meta.worker}`;
  const hydratedRef = useRef(false);
  const [hydrated, setHydrated] = useState(false);
  const autoCitacionRef = useRef(false);
  const autoActaRef = useRef(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const s = JSON.parse(raw);
        if (s.phone) setPhone(s.phone);
        if (s.state) setState(s.state);
        if (s.wa) setWa(s.wa);
        if (s.callRes) setCallRes(s.callRes);
        if (typeof s.isDemo === "boolean") setIsDemo(s.isDemo);
        if (s.turns) setTurns(s.turns);
        if (s.descargo) setDescargo(s.descargo);
        if (s.contrast) setContrast(s.contrast);
        if (s.citacionDoc) { setCitacionDoc(s.citacionDoc); autoCitacionRef.current = true; }
        if (s.actaDoc) { setActaDoc(s.actaDoc); autoActaRef.current = true; }
        if (s.decisionDoc) setDecisionDoc(s.decisionDoc);
        if (s.processId) processIdRef.current = s.processId;
        const cid = s.callRes?.conversation_id;
        if (cid && !(s.turns?.length)) {
          // Hay llamada pero NO la conversación completa: o sigue en curso, o es un
          // proceso viejo guardado antes de la vista de chat. La traemos en ambos casos.
          if (!s.descargo) setWaiting(true);   // sin descargo aún → mostrar "en diligencia"
          pollTranscript(cid);
        }
      }
    } catch {
      /* localStorage no disponible o JSON corrupto — se empieza limpio */
    }
    hydratedRef.current = true;
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey]);

  // Auto-generar la CITACIÓN al inicio (no requiere descargos) → solo descarga/WhatsApp.
  useEffect(() => {
    if (!hydrated || citacionDoc || autoCitacionRef.current) return;
    autoCitacionRef.current = true;
    generateDoc("citacion_descargos");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, citacionDoc]);

  // Auto-generar el ACTA cuando ya hay descargos y AUTO-ENVIARLA al trabajador.
  useEffect(() => {
    if (!hydrated || actaDoc || autoActaRef.current) return;
    if (!descargo.trim()) return;
    autoActaRef.current = true;
    (async () => {
      const d = await generateDoc("acta_descargos");
      // Al terminar la llamada, el acta se envía sola por WhatsApp al trabajador.
      if (d && phone.trim()) sendDocWa(d);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, descargo, actaDoc]);

  useEffect(() => {
    if (!hydratedRef.current) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        phone, state, wa, callRes, isDemo, turns, descargo, contrast,
        citacionDoc, actaDoc, decisionDoc,
        processId: processIdRef.current,
      }));
    } catch {
      /* cuota llena o modo privado — el proceso sigue en memoria */
    }
  }, [storageKey, phone, state, wa, callRes, isDemo, turns, descargo, contrast,
      citacionDoc, actaDoc, decisionDoc]);

  async function sendWhatsApp() {
    setWaLoading(true);
    try {
      // Si hay archivos, súbelos al expediente para que Twilio los adjunte de verdad.
      // (sin process_id el backend manda solo texto — los bytes nunca llegan).
      let processId = processIdRef.current;
      if (evidenceFiles.length > 0) {
        if (!processId) {
          const exp = await createExpediente({
            worker_name: meta.worker,
            worker_id: meta.doc_id ?? meta.worker,
            employer_name: companyName,
            contract_type: "termino_indefinido",
            doc_id: meta.doc_id,
          });
          processId = exp.process_id;
          processIdRef.current = processId;
          // Subir cada archivo (bytes reales → self._blobs en el backend).
          for (const f of evidenceFiles) {
            await uploadDisciplinaryEvidence(processId, f, user?.name ?? "abogado");
          }
        }
      }
      const res = await sendEvidenceWhatsApp({
        to_number: phone,
        worker_name: meta.worker ?? "",
        company_name: companyName ?? "",
        charges_summary: meta.falta ?? "",
        process_id: processId ?? undefined,
        evidence_names: evidence,
        call_date: call.label,
        lawyer_name: user?.name ?? "",
      });
      setWa(res);
      // La CITACIÓN viaja siempre con el primer mensaje (aunque el abogado no
      // adjunte archivos): se genera si falta y se envía como PDF al trabajador.
      if (phone.trim()) {
        const cit = citacionDoc ?? (await generateDoc("citacion_descargos"));
        if (cit) sendDocWa(cit);
      }
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
  // La llamada de descargos dura ~5 min; ElevenLabs además tarda en procesar el
  // transcript y el resumen. Ventana amplia (120 × 5s = 10 min) para no rendirse
  // antes de que la diligencia termine.
  async function pollTranscript(cid: string) {
    pollRef.current = true;
    for (let attempt = 0; attempt < 120 && pollRef.current; attempt++) {
      try {
        const r = await getCallResult(cid);
        // La llamada terminó y ElevenLabs ya entregó la conversación → mostrarla sola.
        const done = r.status === "done" && (r.turns?.length ?? 0) > 0;
        if (done || (r.descargo && r.descargo.trim().length > 0)) {
          if (r.turns?.length) setTurns(r.turns);
          // Descargo para el contraste: el resumen del agente o, si falta, lo que
          // dijo el trabajador en la conversación.
          const dz = r.descargo?.trim() || workerSpeech(r.turns);
          if (dz) setDescargo(dz);
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

  // Respaldo manual: trae la transcripción ahora (por si el polling se agotó o el
  // abogado quiere reintentar tras colgar). Usa el conversation_id de la llamada.
  async function fetchTranscriptNow() {
    const cid = callRes?.conversation_id;
    if (!cid) return;
    setWaiting(true);
    setCallErr(null);
    try {
      const r = await getCallResult(cid);
      if ((r.turns?.length ?? 0) > 0 || r.descargo?.trim()) {
        if (r.turns?.length) setTurns(r.turns);
        const dz = r.descargo?.trim() || workerSpeech(r.turns);
        if (dz) setDescargo(dz);
        setIsDemo(false);
      } else {
        setCallErr("La llamada aún no termina. Intenta de nuevo en un momento.");
      }
    } catch {
      setCallErr("La transcripción aún no está lista. Intenta de nuevo en un momento.");
    } finally {
      setWaiting(false);
    }
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

  // Genera un documento específico (citación / acta / decisión) y lo guarda.
  async function generateDoc(type: DisciplinaryDocType) {
    setGenLoading(type);
    setGenError((p) => (p === type ? null : p));
    try {
      const res = await generateDisciplinaryDocs(
        SESSION, state, descargo || meta.falta, user?.name ?? "",
        {
          worker_name: meta.worker,
          worker_id: meta.doc_id ?? "",
          company_name: companyName,
          charges: meta.falta,
          diligence_date: call.label,
        },
      );
      const d = res.documents.find((x) => x.type === type) ?? null;
      if (type === "citacion_descargos") setCitacionDoc(d);
      else if (type === "acta_descargos") setActaDoc(d);
      else setDecisionDoc(d);
      return d;
    } catch {
      setGenError(type);
      return null;
    } finally {
      setGenLoading(null);
    }
  }

  // Envía un documento generado por WhatsApp como PDF adjunto.
  async function sendDocWa(doc: DisciplinaryDoc) {
    setDocWaSending(doc.type);
    setDocWaResult(null);
    try {
      const r = await sendDocumentWhatsApp({
        to_number: phone, title: doc.title, body_markdown: doc.body_markdown,
        worker_name: meta.worker, company_name: companyName,
      });
      setDocWaResult({ type: doc.type, ok: r.sent, note: r.note });
    } catch {
      setDocWaResult({ type: doc.type, ok: false, note: "Error de red." });
    } finally {
      setDocWaSending(null);
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
              <span className="flex size-8 items-center justify-center rounded-lg bg-carbon text-lienzo">
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
          <EvidencePicker files={evidenceFiles} onChange={setEvidenceFiles} />
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
          {turns.length > 0 ? (
            <div className="space-y-1.5">
              <div className="max-h-80 space-y-2.5 overflow-y-auto rounded-lg border border-n300/60 bg-n100/40 p-3">
                {turns.map((t, i) => (
                  <div
                    key={i}
                    className={cn(
                      "flex flex-col gap-0.5",
                      t.role === "trabajador" ? "items-end" : "items-start",
                    )}
                  >
                    <span className="px-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                      {t.role === "trabajador" ? meta.worker : "Agente · Justo"}
                    </span>
                    <span
                      className={cn(
                        "max-w-[85%] rounded-2xl px-3 py-1.5 text-[13px] leading-snug",
                        t.role === "trabajador"
                          ? "bg-acento text-white"
                          : "bg-card text-toga border border-n300/60",
                      )}
                    >
                      {t.message}
                    </span>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground">
                Conversación completa de la diligencia (ElevenLabs) · {turns.length} intervenciones.
              </p>
            </div>
          ) : descargo ? (
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
              En diligencia… la llamada puede durar varios minutos. La transcripción aparecerá al finalizar.
            </p>
          ) : callRes?.conversation_id ? (
            <div className="space-y-2 rounded-lg border border-dashed border-n300 bg-n100/40 px-3.5 py-3">
              <p className="text-sm text-muted-foreground">
                La llamada se realizó. Si ya colgó, trae la transcripción del descargo.
              </p>
              <Button variant="secondary" size="sm" onClick={fetchTranscriptNow} className="gap-1.5">
                <MessageSquareText className="size-4" />
                Traer transcripción
              </Button>
            </div>
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

        {/* Paso 4 — Documentos del proceso (progresivos) */}
        <section className={card}>
          <StepHeader
            icon={FileText}
            n={4}
            title="Documentos del proceso"
            done={Boolean(citacionDoc && actaDoc && decisionDoc)}
          />
          <div className="space-y-3">
            {/* 1) Citación a descargos — se genera sola al inicio, para enviar por WhatsApp */}
            <DocStage
              auto
              label="Citación a descargos"
              hint="Se genera automáticamente para enviarla al trabajador por WhatsApp."
              doc={citacionDoc}
              generating={genLoading === "citacion_descargos"}
              error={genError === "citacion_descargos"}
              onGenerate={() => generateDoc("citacion_descargos")}
              onSendWa={citacionDoc ? () => sendDocWa(citacionDoc) : undefined}
              sending={docWaSending === "citacion_descargos"}
              waResult={docWaResult?.type === "citacion_descargos" ? docWaResult : null}
            />

            {/* 2) Acta de la diligencia — se genera sola tras los descargos, también por WhatsApp */}
            <DocStage
              auto
              label="Acta de la diligencia de descargos"
              hint="Se genera automáticamente con los descargos para enviarla por WhatsApp."
              doc={actaDoc}
              generating={genLoading === "acta_descargos"}
              error={genError === "acta_descargos"}
              onGenerate={() => generateDoc("acta_descargos")}
              disabled={!descargo.trim()}
              disabledHint="Disponible cuando se tomen los descargos en la llamada."
              onSendWa={actaDoc ? () => sendDocWa(actaDoc) : undefined}
              sending={docWaSending === "acta_descargos"}
              waResult={docWaResult?.type === "acta_descargos" ? docWaResult : null}
            />

            {/* 3) Decisión final — habilitada para generar cuando están citación + acta */}
            <DocStage
              label="Decisión final"
              hint="Habilitada para generar. Si el debido proceso está incompleto, el documento saldrá con la advertencia de nulidad del Guardián."
              doc={decisionDoc}
              generating={genLoading === "decision_final"}
              error={genError === "decision_final"}
              onGenerate={() => generateDoc("decision_final")}
              disabled={!citacionDoc || !actaDoc}
              disabledHint="Se habilita cuando estén la citación y el acta de descargos."
            />
          </div>
        </section>
      </div>
    </div>
  );
}

// Una etapa de documento. `auto`: se genera sola (citación/acta) → sin botón
// Generar; solo descarga/preview/WhatsApp. Sin `auto` (decisión): botón habilitado.
function DocStage({
  auto, label, hint, doc, generating, error, onGenerate, disabled, disabledHint,
  blocked, blockedHint, onSendWa, sending, waResult,
}: {
  auto?: boolean;
  label: string;
  hint: string;
  doc: DisciplinaryDoc | null;
  generating: boolean;
  error?: boolean;
  onGenerate: () => void;
  disabled?: boolean;
  disabledHint?: string;
  blocked?: boolean;
  blockedHint?: string;
  onSendWa?: () => void;
  sending?: boolean;
  waResult?: { ok: boolean; note?: string } | null;
}) {
  if (blocked) {
    return (
      <div className="rounded-lg border border-n300/60 bg-card px-3.5 py-3">
        <div className="flex items-center gap-2">
          <Lock className="size-4 text-muted-foreground" aria-hidden />
          <span className="flex-1 text-sm font-medium text-muted-foreground">{label}</span>
          <span className="badge-bloqueado">bloqueado</span>
        </div>
        {blockedHint && <p className="mt-1.5 text-xs text-warn-fg">{blockedHint}</p>}
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="rounded-lg border border-dashed border-n300 bg-n100/40 px-3.5 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <FileText className="size-4 text-muted-foreground" aria-hidden />
          <span className="flex-1 text-sm font-medium text-toga">{label}</span>
          {generating ? (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-acento">
              <Loader2 className="size-3.5 animate-spin" /> Generando…
            </span>
          ) : auto && !disabled && !error ? (
            // Pendiente de auto-generación (transitorio) — sin botón.
            <span className="text-xs text-muted-foreground">En cola…</span>
          ) : (
            // Decisión final (manual) o reintento tras error/disabled levantado.
            <Button size="sm" onClick={onGenerate} disabled={disabled}>
              <FileText className="size-4" />
              {error ? "Reintentar" : "Generar"}
            </Button>
          )}
        </div>
        <p className={cn("mt-1.5 text-xs", error ? "text-warn-fg" : "text-muted-foreground")}>
          {error
            ? "No se pudo generar. Reintenta."
            : disabled && disabledHint
              ? disabledHint
              : hint}
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-n300/60 bg-card">
      <DocCardInner doc={doc} onSendWa={onSendWa} sending={sending} waResult={waResult} />
    </div>
  );
}

// Estilo del preview del documento (mismo look que la subsanación).
const DOC_PREVIEW_STYLE = `
  .doc-md{font-size:13px;line-height:1.55;color:#2B2B2B}
  .doc-md h1,.doc-md h2,.doc-md h3{font-weight:600;margin:.7rem 0 .35rem}
  .doc-md h1{font-size:15px}.doc-md h2{font-size:14px}.doc-md h3{font-size:13px}
  .doc-md p{margin:.4rem 0}
  .doc-md ul,.doc-md ol{margin:.4rem 0 .4rem 1.1rem}
  .doc-md li{margin:.15rem 0}
  .doc-md strong{font-weight:600}
  .doc-md hr{border:none;border-top:1px solid #e5e7eb;margin:.7rem 0}
`;

function DocCardInner({
  doc, onSendWa, sending, waResult,
}: {
  doc: DisciplinaryDoc;
  onSendWa?: () => void;
  sending?: boolean;
  waResult?: { ok: boolean; note?: string } | null;
}) {
  const [open, setOpen] = useState(false);
  const html = useMemo(() => marked.parse(doc.body_markdown) as string, [doc.body_markdown]);

  return (
    <>
      <div className="flex flex-wrap items-center gap-2 px-3.5 py-2.5">
        <FileText className="size-4 text-acento" aria-hidden />
        <span className="flex-1 text-sm font-medium text-toga">{doc.title}</span>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-1.5 rounded-md border border-n300/60 px-2 py-1 text-xs font-medium text-toga transition-colors hover:bg-n100"
        >
          <Eye className="size-3.5" />
          {open ? "Ocultar" : "Ver"}
        </button>
        <button
          type="button"
          onClick={() => downloadAsWord(doc.title, doc.body_markdown)}
          className="inline-flex items-center gap-1.5 rounded-md border border-acento/30 bg-acento/5 px-2 py-1 text-xs font-medium text-acento transition-colors hover:bg-acento/10"
        >
          <Download className="size-3.5" />
          Word
        </button>
        <button
          type="button"
          onClick={() => downloadAsPdf(doc.title, doc.body_markdown)}
          className="inline-flex items-center gap-1.5 rounded-md border border-acento/30 bg-acento/5 px-2 py-1 text-xs font-medium text-acento transition-colors hover:bg-acento/10"
        >
          <Download className="size-3.5" />
          PDF
        </button>
        {onSendWa && (
          <button
            type="button"
            onClick={onSendWa}
            disabled={sending}
            className="inline-flex items-center gap-1.5 rounded-md bg-acento px-2 py-1 text-xs font-medium text-white transition-colors hover:bg-acento/90 disabled:opacity-60"
          >
            {sending ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />}
            WhatsApp
          </button>
        )}
      </div>
      {waResult && (
        <p className={cn(
          "px-3.5 pb-2 text-[11px]",
          waResult.ok ? "text-ok-fg" : "text-warn-fg",
        )}>
          {waResult.ok ? "✓ Documento enviado por WhatsApp." : (waResult.note || "No se pudo enviar.")}
        </p>
      )}
      {open && (
        <div className="border-t border-n300/50 bg-n100/40 px-4 py-3">
          <style dangerouslySetInnerHTML={{ __html: DOC_PREVIEW_STYLE }} />
          <div className="doc-md" dangerouslySetInnerHTML={{ __html: html }} />
        </div>
      )}
    </>
  );
}

function EvidencePicker({
  files,
  onChange,
}: {
  files: File[];
  onChange: (v: File[]) => void;
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
            const picked = Array.from(e.target.files ?? []);
            if (picked.length) onChange([...files, ...picked]);
            e.currentTarget.value = "";
          }}
        />
      </label>
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((f, i) => (
            <span
              key={`${f.name}-${i}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-n300/60 bg-card px-2.5 py-1 text-[12px] text-toga"
            >
              {f.name}
              <button
                type="button"
                onClick={() => onChange(files.filter((_, j) => j !== i))}
                className="text-muted-foreground hover:text-risk-fg"
                aria-label={`Quitar ${f.name}`}
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
