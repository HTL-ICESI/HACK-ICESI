"use client";

import { useEffect, useRef, useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ExtractedRecord } from "@/components/compliance/ExtractedRecord";
import { GapsList } from "@/components/compliance/GapsList";
import { LiquidationTable } from "@/components/compliance/LiquidationTable";
import { RemediationPanel } from "@/components/compliance/RemediationPanel";
import { getBatchResult } from "@/lib/api";
import type { BatchItem, BatchResult } from "@/lib/types";

interface Span { start: number; end: number }

/** Renderiza el texto completo con el span resaltado y hace auto-scroll hacia él. */
function ContractTextView({ text, highlight }: { text: string; highlight: Span | null }) {
  const markRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (highlight && markRef.current) {
      markRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlight]);

  if (!highlight) {
    return (
      <pre className="max-h-[55vh] overflow-y-auto whitespace-pre-wrap px-4 py-3 font-mono text-xs leading-relaxed text-toga">
        {text}
      </pre>
    );
  }

  const before = text.slice(0, highlight.start);
  const match  = text.slice(highlight.start, highlight.end);
  const after  = text.slice(highlight.end);

  return (
    <pre className="max-h-[55vh] overflow-y-auto whitespace-pre-wrap px-4 py-3 font-mono text-xs leading-relaxed text-toga">
      {before}
      <mark
        ref={markRef}
        className="rounded bg-acento/20 px-0.5 font-semibold text-acento not-italic outline outline-1 outline-acento/40"
      >
        {match}
      </mark>
      {after}
    </pre>
  );
}

export function ContractModal({
  batchId,
  item,
  open,
  onClose,
}: {
  batchId: string;
  item: BatchItem | null;
  open: boolean;
  onClose: () => void;
}) {
  const [result, setResult]           = useState<BatchResult | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [activeTab, setActiveTab]     = useState("datos");
  const [highlight, setHighlight]     = useState<Span | null>(null);

  useEffect(() => {
    setResult(null);
    setError(null);
    setActiveTab("datos");
    setHighlight(null);
    if (!open || !item || item.status !== "done") return;
    let active = true;
    getBatchResult(batchId, item.doc_id)
      .then((r) => active && setResult(r))
      .catch((e) => active && setError(e instanceof Error ? e.message : "Error"));
    return () => { active = false; };
  }, [open, item, batchId]);

  function handleGoToContract(span: Span) {
    setHighlight(span);
    setActiveTab("contrato");
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-display">
            {item?.summary?.worker_name ?? item?.filename ?? "Contrato"}
          </DialogTitle>
        </DialogHeader>

        {error && (
          <p className="text-sm text-risk-fg">No se pudo cargar el detalle: {error}</p>
        )}
        {!result && !error && (
          <p className="py-8 text-center text-sm text-muted-foreground">Cargando análisis…</p>
        )}

        {result && (
          <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); if (v !== "contrato") setHighlight(null); }} className="mt-2">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="datos">Datos</TabsTrigger>
              <TabsTrigger value="contrato">Contrato</TabsTrigger>
              <TabsTrigger value="riesgos">
                Riesgos ({result.compliance.gaps.length})
              </TabsTrigger>
              <TabsTrigger value="liquidacion">Liquidación</TabsTrigger>
              <TabsTrigger value="subsanacion" disabled={!result.remediation}>
                Subsanación
              </TabsTrigger>
            </TabsList>

            <TabsContent value="datos" className="mt-4">
              <ExtractedRecord
                record={result.extract.record}
                docText={result.text}
                onGoToContract={handleGoToContract}
              />
            </TabsContent>

            <TabsContent value="contrato" className="mt-4">
              <div className="rounded-lg border border-n300/60 bg-card">
                <div className="flex items-center justify-between border-b border-n300/50 px-4 py-2">
                  <span className="text-xs font-medium text-muted-foreground">
                    {result.filename}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Texto completo extraído (M1)
                  </span>
                </div>
                <ContractTextView
                  text={result.text || "Sin texto disponible."}
                  highlight={highlight}
                />
              </div>
            </TabsContent>

            <TabsContent value="riesgos" className="mt-4">
              {result.compliance.gaps.length ? (
                <GapsList gaps={result.compliance.gaps} />
              ) : (
                <p className="rounded-lg border border-ok/30 bg-ok-soft p-4 text-sm text-ok-fg">
                  Sin riesgos detectados — el contrato es conforme.
                </p>
              )}
            </TabsContent>

            <TabsContent value="liquidacion" className="mt-4">
              <LiquidationTable data={result.liquidation} />
            </TabsContent>

            <TabsContent value="subsanacion" className="mt-4">
              {result.remediation ? (
                <RemediationPanel data={result.remediation} />
              ) : (
                <p className="text-sm text-muted-foreground">Sin documento de subsanación.</p>
              )}
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
}
