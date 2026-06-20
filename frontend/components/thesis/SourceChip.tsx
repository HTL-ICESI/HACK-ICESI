"use client";

import { ArrowRight, FileText } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { formatConfidence } from "@/lib/format";
import type { Citation, Source } from "@/lib/types";

const CONTEXT_CHARS = 160;

interface SourceChipProps {
  source?: Source | null;
  citation?: Citation | null;
  label?: string;
  /** Texto completo del documento para mostrar contexto alrededor del span. */
  docText?: string | null;
  /** Callback que navega a la pestaña Contrato y resalta el span. */
  onGoToContract?: (span: { start: number; end: number }) => void;
}

/** Extrae [before, match, after] con ±CONTEXT_CHARS alrededor del span. */
function buildContext(
  docText: string,
  start: number,
  end: number,
): { before: string; match: string; after: string; truncBefore: boolean; truncAfter: boolean } {
  const rawBefore = docText.slice(Math.max(0, start - CONTEXT_CHARS), start);
  const rawAfter  = docText.slice(end, end + CONTEXT_CHARS);
  return {
    before:      rawBefore,
    match:       docText.slice(start, end),
    after:       rawAfter,
    truncBefore: start - CONTEXT_CHARS > 0,
    truncAfter:  end + CONTEXT_CHARS < docText.length,
  };
}

export function SourceChip({ source, citation, label, docText, onGoToContract }: SourceChipProps) {
  if (!source && !citation) return null;

  const chipLabel =
    label ?? (citation ? `${citation.norm_id} ${citation.article}` : "fuente");

  const hasContext =
    !!docText &&
    source != null &&
    typeof source.span_start === "number" &&
    typeof source.span_end === "number";

  const ctx = hasContext
    ? buildContext(docText!, source!.span_start, source!.span_end)
    : null;

  return (
    <Dialog>
      <DialogTrigger className="chip-fuente" aria-label="Ver fuente">
        <FileText className="size-3" aria-hidden="true" />
        {chipLabel}
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display">Fuente verificable</DialogTitle>
        </DialogHeader>

        {citation && (
          <div className="space-y-1">
            <div className="text-sm font-medium text-toga">{citation.title}</div>
            <div className="font-mono text-[12px] text-muted-foreground">
              {citation.norm_id} · {citation.article}
            </div>
            <a
              href={citation.url}
              target="_blank"
              rel="noreferrer"
              className="block break-all font-mono text-[12px] text-acento underline-offset-2 hover:underline"
            >
              {citation.url}
            </a>
            <span className={citation.verified ? "badge-calculado w-fit" : "badge-revisar w-fit"}>
              {citation.verified ? "norma verificada" : "norma sin verificar"}
            </span>
          </div>
        )}

        {source && (
          <div className="space-y-3">
            {/* Contexto con highlight — muestra el fragmento en su entorno */}
            <div className="rounded-md border border-n300/60 bg-n100 px-3 py-2.5 font-mono text-[12px] leading-relaxed text-toga">
              {ctx ? (
                <>
                  {ctx.truncBefore && (
                    <span className="text-muted-foreground">…</span>
                  )}
                  <span className="text-muted-foreground">{ctx.before}</span>
                  <mark className="rounded bg-acento/15 px-0.5 font-semibold text-acento not-italic">
                    {ctx.match}
                  </mark>
                  <span className="text-muted-foreground">{ctx.after}</span>
                  {ctx.truncAfter && (
                    <span className="text-muted-foreground">…</span>
                  )}
                </>
              ) : (
                <span>«{source.text}»</span>
              )}
            </div>

            <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
              <span>
                span {source.span_start}–{source.span_end} · {source.doc_id}
              </span>
              <span>confianza {formatConfidence(source.confidence)}</span>
            </div>
            <Progress value={Math.round(source.confidence * 100)} />

            {/* Botón para ir al contrato y ver el fragmento resaltado */}
            {onGoToContract && source.span_start != null && (
              <DialogTrigger asChild>
                <button
                  onClick={() =>
                    onGoToContract({ start: source.span_start, end: source.span_end })
                  }
                  className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-acento/30 bg-acento/5 py-2 text-[12px] font-medium text-acento transition-colors hover:bg-acento/10"
                >
                  Ver en el contrato
                  <ArrowRight className="size-3.5" />
                </button>
              </DialogTrigger>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
