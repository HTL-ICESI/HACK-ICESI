"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Download, Edit3, Eye, FileText, Lock, X } from "lucide-react";
import { marked } from "marked";

import { SourceChip } from "@/components/thesis/SourceChip";
import { StatusBadge } from "@/components/thesis/StatusBadge";
import { Button } from "@/components/ui/button";
import { downloadAsWord, downloadAsPdf } from "@/lib/docExport";
import type { RemediationResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

// Configurar marked para que genere HTML seguro y limpio.
marked.setOptions({ breaks: true, gfm: true } as never);

const PREVIEW_STYLE = `
  .md-preview h2{font-size:1rem;font-weight:600;color:#11113a;margin:1rem 0 .4rem}
  .md-preview h3{font-size:.875rem;font-weight:600;color:#11113a;margin:.8rem 0 .3rem}
  .md-preview p{margin:.4rem 0;line-height:1.6;font-size:.875rem;color:#554B45}
  .md-preview strong{color:#11113a;font-weight:600}
  .md-preview ul{list-style:disc;padding-left:1.25rem;margin:.4rem 0}
  .md-preview li{font-size:.875rem;color:#554B45;margin:.2rem 0}
  .md-preview blockquote{border-left:3px solid #3B43C9;margin:.5rem 0;padding:.4rem .8rem;background:#f5f5ff;border-radius:0 6px 6px 0;color:#555;font-style:italic;font-size:.8rem}
  .md-preview table{border-collapse:collapse;width:100%;font-size:.8rem;margin:.6rem 0}
  .md-preview th{background:#f3f4f6;border:1px solid #d1d5db;padding:6px 10px;text-align:left;font-weight:600;color:#11113a}
  .md-preview td{border:1px solid #d1d5db;padding:6px 10px;color:#554B45}
  .md-preview hr{border:none;border-top:1px solid #e5e7eb;margin:.8rem 0}
  .md-preview code{background:#f3f4f6;border-radius:3px;padding:1px 4px;font-size:.75rem}
`;

function MarkdownPreview({ content }: { content: string }) {
  const html = marked.parse(content) as string;
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: PREVIEW_STYLE }} />
      <div className="md-preview" dangerouslySetInnerHTML={{ __html: html }} />
    </>
  );
}

export function RemediationPanel({ data }: { data: RemediationResponse }) {
  const [approved, setApproved] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(data.body_markdown);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const blocked = data.validation.blocked;

  // Autosize del textarea al abrir.
  useEffect(() => {
    if (editing && textareaRef.current) {
      const el = textareaRef.current;
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    }
  }, [editing]);

  function handleTextareaInput() {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${el.scrollHeight}px`;
    }
  }

  function discardEdits() {
    setDraft(data.body_markdown);
    setEditing(false);
  }

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "overflow-hidden rounded-2xl border bg-card shadow-bezel",
          blocked ? "border-risk/40" : "border-n300/60",
        )}
      >
        {/* ── Cabecera ─────────────────────────────────────────────────── */}
        <div
          className={cn(
            "flex items-center justify-between gap-3 border-b px-5 py-3",
            blocked ? "border-risk/30 bg-risk-soft" : "border-n300/60 bg-n100/60",
          )}
        >
          <div className="flex min-w-0 items-center gap-2">
            <FileText className="size-4 shrink-0 text-muted-foreground" />
            <p className="truncate text-sm font-medium text-toga">{data.title}</p>
          </div>
          <div className="flex items-center gap-2">
            {!blocked && !editing && (
              <button
                onClick={() => setEditing(true)}
                title="Editar borrador"
                className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-acento hover:bg-acento/8 transition-colors"
              >
                <Edit3 className="size-3" /> Editar
              </button>
            )}
            {editing && (
              <button
                onClick={discardEdits}
                title="Descartar cambios"
                className="inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-risk hover:bg-risk-soft transition-colors"
              >
                <X className="size-3" /> Descartar
              </button>
            )}
            <StatusBadge kind="revisar" />
          </div>
        </div>

        {/* ── Cuerpo: preview o editor ──────────────────────────────────── */}
        <div className="px-5 py-5">
          {editing ? (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <Edit3 className="size-3" />
                Editando — el texto marcado con ** ** es negrita, ## es título.
              </div>
              <textarea
                ref={textareaRef}
                value={draft}
                onChange={(e) => {
                  setDraft(e.target.value);
                  handleTextareaInput();
                }}
                onInput={handleTextareaInput}
                className="w-full resize-none rounded-lg border border-acento/40 bg-white p-3 font-mono text-xs leading-relaxed text-toga outline-none focus:ring-2 focus:ring-acento/20 min-h-[260px]"
                spellCheck={false}
              />
              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => setEditing(false)}
                  className="inline-flex items-center gap-1.5 rounded-md bg-acento px-3 py-1.5 text-xs font-medium text-white hover:bg-acento/90 transition-colors"
                >
                  <Eye className="size-3" /> Ver preview
                </button>
              </div>
            </div>
          ) : (
            <MarkdownPreview content={draft} />
          )}

          {data.citations.length > 0 && !editing && (
            <div className="mt-5 flex flex-wrap gap-2 border-t border-n300/40 pt-4">
              {data.citations.map((c, i) => (
                <SourceChip key={`${c.norm_id}-${i}`} citation={c} />
              ))}
            </div>
          )}
        </div>

        {/* ── Descargas ──────────────────────────────────────────────────── */}
        {!blocked && (
          <div className="flex flex-wrap items-center gap-2 border-t border-n300/60 bg-n100/40 px-5 py-3">
            <span className="mr-1 text-xs text-muted-foreground">Descargar borrador:</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadAsWord(data.title, draft)}
              title="Descarga .docx — abre en Word y Google Docs"
            >
              <Download className="size-3.5" /> Word (.docx)
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadAsPdf(data.title, draft)}
              title="Abre diálogo de impresión → Guardar como PDF"
            >
              <Download className="size-3.5" /> PDF
            </Button>
            {draft !== data.body_markdown && (
              <span className="ml-2 text-[11px] text-acento">
                * descargará la versión editada
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── Estado de aprobación ──────────────────────────────────────────── */}
      {blocked ? (
        <div className="flex items-start gap-3 rounded-lg border border-risk/40 bg-risk-soft p-4">
          <Lock className="mt-0.5 size-4 shrink-0 text-risk" />
          <div>
            <p className="text-sm font-medium text-risk-fg">
              Las cifras del documento no coinciden con el motor.
            </p>
            <p className="text-sm text-risk-fg/90">
              Documento bloqueado — no se puede aprobar.
            </p>
          </div>
        </div>
      ) : approved ? (
        <div className="flex items-center gap-2 rounded-lg border border-ok/30 bg-ok-soft px-4 py-3">
          <Check className="size-4 text-ok" />
          <p className="text-sm font-medium text-ok-fg">
            Validado y aprobado por el abogado.
          </p>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => setApproved(true)}>Validar y aprobar</Button>
          <span className="text-xs text-muted-foreground">
            El abogado firma; el sistema asiste.
          </span>
        </div>
      )}
    </div>
  );
}
