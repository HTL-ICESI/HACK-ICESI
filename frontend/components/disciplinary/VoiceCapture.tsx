"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Square } from "lucide-react";

import { cn } from "@/lib/utils";

interface Segment {
  speaker: "instructor" | "trabajador";
  text: string;
}

// Guion del caso de demostración. En producción, el transcript llega de
// POST /api/disciplinary/transcribe (Web Audio API -> STT); aquí se revela
// progresivamente para simular la transcripción en vivo (fallback sin micrófono).
const SEGMENTS: Segment[] = [
  {
    speaker: "instructor",
    text: "Siendo las 10:00 a.m. se da inicio a la diligencia de descargos del trabajador.",
  },
  {
    speaker: "instructor",
    text: "Se le informa el motivo: presunta falta al reglamento interno de trabajo.",
  },
  {
    speaker: "trabajador",
    text: "Manifiesto que no fui notificado con la debida antelación.",
  },
  {
    speaker: "instructor",
    text: "Se deja constancia de la respuesta del trabajador.",
  },
];

const SPEAKER_LABEL: Record<Segment["speaker"], string> = {
  instructor: "Instructor",
  trabajador: "Trabajador",
};

const REVEAL_MS = 1300;

export function VoiceCapture() {
  const [recording, setRecording] = useState(false);
  const [shown, setShown] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  function toggle() {
    if (recording) {
      setRecording(false);
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    setRecording(true);
    if (shown >= SEGMENTS.length) setShown(0);
    intervalRef.current = setInterval(() => {
      setShown((n) => {
        const next = n + 1;
        if (next >= SEGMENTS.length && intervalRef.current) {
          clearInterval(intervalRef.current);
        }
        return Math.min(next, SEGMENTS.length);
      });
    }, REVEAL_MS);
  }

  const segments = SEGMENTS.slice(0, shown);

  return (
    <div className="rounded-2xl border border-n300/60 bg-card p-5 shadow-hairline">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggle}
          className={cn(
            "flex size-11 items-center justify-center rounded-full text-lienzo transition-colors",
            recording ? "bg-risk" : "bg-toga hover:bg-toga-700",
          )}
          aria-label={recording ? "Detener grabación" : "Grabar descargos"}
        >
          {recording ? (
            <Square className="size-4" />
          ) : (
            <Mic className="size-5" />
          )}
        </button>
        <div>
          <p className="text-sm font-medium text-toga">
            {recording ? "Grabando descargos…" : "Captura de voz"}
          </p>
          <p className="text-xs text-muted-foreground">
            {recording
              ? "Transcribiendo en vivo"
              : "Pulsa para grabar y transcribir la diligencia"}
          </p>
        </div>
        {recording && (
          <span className="ml-auto flex items-center gap-1.5 font-mono text-xs text-risk-fg">
            <span className="size-2 animate-pulse rounded-full bg-risk" />
            REC
          </span>
        )}
      </div>

      {/* Región viva siempre presente para que el lector de pantalla anuncie
          cada segmento nuevo de la transcripción (DESIGN.md §0 · a11y). */}
      <div
        role="log"
        aria-live="polite"
        aria-label="Transcripción de la diligencia"
        className={
          segments.length > 0
            ? "mt-4 space-y-2 border-t border-n300/50 pt-4"
            : undefined
        }
      >
        {segments.map((seg, i) => (
          <div
            key={i}
            className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300"
          >
            <span className="mr-2 font-mono text-[11px] uppercase tracking-wide text-acento">
              {SPEAKER_LABEL[seg.speaker]}
            </span>
            <span className="text-sm text-body">{seg.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
