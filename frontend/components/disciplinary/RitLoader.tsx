"use client";

import { useEffect, useRef, useState } from "react";
import { Eye, FileCheck2, Loader2, Upload } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ingest } from "@/lib/api";

export interface RitRef {
  doc_id: string;
  filename: string;
  /** Texto del reglamento (extraído por M1 al subir, o el provisional sembrado). */
  text?: string;
  /** true = RIT provisional precargado en la BD demo (no subido por el usuario). */
  seeded?: boolean;
}

// RIT provisional precargado en la "BD" demo de la empresa. Permite mostrar el flujo
// disciplinario con un reglamento ya cargado y visualizable, sin subir nada.
const SEED_RIT: RitRef = {
  doc_id: "rit-2026-hg",
  filename: "RIT-2026-HG",
  seeded: true,
  text: `REGLAMENTO INTERNO DE TRABAJO — RIT-2026-HG
Hurtado Gandini & Asociados SAS · Vigencia 2026

CAPÍTULO VIII — RÉGIMEN DISCIPLINARIO Y DEBIDO PROCESO

Artículo 42. Faltas. Constituye falta toda acción u omisión del trabajador que
contraríe las obligaciones y prohibiciones del presente reglamento, el contrato
de trabajo o la ley. Las faltas se clasifican en leves, graves y gravísimas.

Artículo 43. Procedimiento. Antes de imponer cualquier sanción disciplinaria, el
empleador adelantará un procedimiento que garantice el debido proceso (C.N. art.
29; C.S.T. art. 115), el cual comprende:
  a) Comunicación formal y escrita de la apertura del proceso.
  b) Formulación concreta de los cargos imputados.
  c) Traslado y acceso a las pruebas que sustentan los cargos.
  d) Término mínimo de defensa no inferior a cinco (5) días hábiles.
  e) Oportunidad de rendir descargos, con derecho a ser acompañado por dos (2)
     representantes del sindicato o dos (2) compañeros de trabajo.
  f) Decisión motivada y notificada, con derecho a impugnación.

Artículo 44. Sanciones. Según la gravedad y la reincidencia: llamado de atención,
suspensión hasta por ocho (8) días en la primera vez y hasta dos (2) meses en
caso de reincidencia, o terminación del contrato por justa causa.

Artículo 45. Tipicidad. Ninguna sanción podrá imponerse por una falta que no esté
previamente tipificada en este reglamento o en la ley (C.S.T. art. 114).`,
};

function storageKey(companyId: string) {
  return `rit:${companyId}`;
}

/** RIT persistido por empresa (provisional). Cae al RIT sembrado si no hay uno subido. */
function loadStored(companyId: string): RitRef {
  try {
    const raw = localStorage.getItem(storageKey(companyId));
    return raw ? (JSON.parse(raw) as RitRef) : SEED_RIT;
  } catch {
    return SEED_RIT;
  }
}

/**
 * Carga el Reglamento Interno de Trabajo de la empresa.
 * El RIT es un documento, no un texto: viene precargado (provisional) y se puede
 * visualizar; si se sube uno nuevo, se envía al backend (M1) y reemplaza al anterior.
 */
export function RitLoader({
  companyId,
  onChange,
}: {
  companyId: string;
  onChange: (rit: RitRef | null) => void;
}) {
  const [rit, setRit] = useState<RitRef | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewing, setViewing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Recupera (o siembra) el RIT de esta empresa al montar / cambiar de empresa.
  useEffect(() => {
    const stored = loadStored(companyId);
    setRit(stored);
    onChange(stored);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    try {
      const res = await ingest(file);
      const next: RitRef = { doc_id: res.doc_id, filename: file.name, text: res.text };
      localStorage.setItem(storageKey(companyId), JSON.stringify(next));
      setRit(next);
      onChange(next);
    } catch {
      setError("No se pudo cargar el RIT. Intenta de nuevo.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-toga">RIT de la empresa</label>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.doc,.docx,.txt"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />

      {rit ? (
        <div className="flex items-center gap-3 rounded-lg border border-ok/30 bg-ok-soft/40 px-3.5 py-2.5">
          <FileCheck2 className="size-4 shrink-0 text-ok-fg" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="truncate font-mono text-sm font-medium text-toga">
              {rit.filename}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {rit.seeded ? "RIT cargado · provisional" : "RIT cargado"}
            </p>
          </div>
          {rit.text && (
            <button
              type="button"
              onClick={() => setViewing(true)}
              className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-acento transition-colors hover:bg-acento-soft"
            >
              <Eye className="size-3.5" aria-hidden />
              Ver
            </button>
          )}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-n100 hover:text-toga disabled:opacity-50"
          >
            {uploading ? <Loader2 className="size-3.5 animate-spin" /> : "Reemplazar"}
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-n300 bg-n100/40 px-3.5 py-3 text-sm font-medium text-toga transition-colors hover:border-acento/40 hover:bg-acento/5 disabled:opacity-60"
        >
          {uploading ? (
            <>
              <Loader2 className="size-4 animate-spin" aria-hidden />
              Cargando RIT…
            </>
          ) : (
            <>
              <Upload className="size-4" aria-hidden />
              Cargar RIT
            </>
          )}
        </button>
      )}

      {error ? (
        <p className="text-xs text-risk-fg">{error}</p>
      ) : (
        <p className="text-xs text-muted-foreground">
          Reglamento Interno de Trabajo aplicable a esta empresa.
        </p>
      )}

      {/* Visor del RIT */}
      <Dialog open={viewing} onOpenChange={setViewing}>
        <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-mono text-base">
              {rit?.filename}
            </DialogTitle>
          </DialogHeader>
          <pre className="whitespace-pre-wrap rounded-lg bg-n100/60 p-4 font-mono text-[12px] leading-relaxed text-[#554B45]">
            {rit?.text}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  );
}
