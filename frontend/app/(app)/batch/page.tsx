"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Plus, X } from "lucide-react";

import { BatchDropzone } from "@/components/batch/BatchDropzone";
import { BatchProgress } from "@/components/batch/BatchProgress";
import { BatchDashboardHeader } from "@/components/batch/BatchDashboardHeader";
import { BatchFilters, type BatchFilterState } from "@/components/batch/BatchFilters";
import { ContractCard } from "@/components/batch/ContractCard";
import { ContractModal } from "@/components/batch/ContractModal";
import { useBatchStatus } from "@/hooks/useBatchStatus";
import { batchIngest, getBatchLatest } from "@/lib/api";
import type { BatchItem } from "@/lib/types";

function BatchContent() {
  const searchParams = useSearchParams();

  const [batchId, setBatchId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<BatchItem | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [filters, setFilters] = useState<BatchFilterState>({
    query: "",
    risk: "todos",
    gap: searchParams.get("gap") ?? "todos",
  });

  // Al entrar, recupera el último lote del backend (ahora persistido en BD, así que
  // sobrevive a reinicios) y aplica el gap de la URL (viene del dashboard).
  useEffect(() => {
    let active = true;
    getBatchLatest()
      .then((r) => { if (active && r.batch_id) setBatchId(r.batch_id); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  // Si la URL cambia (navegación desde alerta del dashboard), actualiza el filtro de gap.
  useEffect(() => {
    const gap = searchParams.get("gap") ?? "todos";
    setFilters((prev) => ({ ...prev, gap }));
  }, [searchParams]);

  const { status, error } = useBatchStatus(batchId);

  async function handleFiles(files: File[]) {
    setUploading(true);
    setUploadError(null);
    try {
      const res = await batchIngest(files);
      setBatchId(res.batch_id);
      setShowUpload(false);
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "No se pudo iniciar el lote.");
    } finally {
      setUploading(false);
    }
  }

  const doneItems = useMemo(
    () => (status?.results ?? []).filter((i) => i.status === "done" && i.summary),
    [status],
  );

  const filtered = useMemo(() => {
    return doneItems.filter((i) => {
      const s = i.summary!;
      if (filters.risk !== "todos" && s.risk_level !== filters.risk) return false;
      if (filters.gap !== "todos" && !s.gaps.some((g) => g.gap_id === filters.gap)) return false;
      if (filters.query.trim()) {
        const q = filters.query.trim().toLowerCase();
        if (!s.worker_name.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [doneItems, filters]);

  const hasBatch = Boolean(batchId && status);

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 md:py-10">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="font-display text-3xl font-medium text-toga">Compliance</h1>
          <p className="mt-1 text-[15px] text-muted-foreground">
            Sube los contratos del cliente — semáforos de riesgo, exposición económica y
            subsanación lista para cada uno.
          </p>
        </div>
        {hasBatch && !showUpload && (
          <button
            onClick={() => setShowUpload(true)}
            className="mt-1 inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-acento/30 bg-acento/5 px-3.5 py-2 text-sm font-medium text-acento transition-colors hover:bg-acento/10"
          >
            <Plus className="size-4" aria-hidden />
            Subir más contratos
          </button>
        )}
      </header>

      {/* Dropzone: visible cuando no hay batch o cuando el usuario abre el toggle */}
      {(!hasBatch || showUpload) && (
        <div className="mb-6">
          {showUpload && (
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-medium text-toga">Agregar más contratos al análisis</p>
              <button
                onClick={() => setShowUpload(false)}
                className="rounded p-1 text-muted-foreground hover:text-toga"
                aria-label="Cancelar"
              >
                <X className="size-4" />
              </button>
            </div>
          )}
          <BatchDropzone onFiles={handleFiles} busy={uploading} />
          {uploadError && <p className="mt-3 text-sm text-risk-fg">{uploadError}</p>}
        </div>
      )}

      {hasBatch && status && (
        <div className="space-y-6">
          {status.completed < status.total && <BatchProgress status={status} />}
          {error && <p className="text-sm text-risk-fg">Error de polling: {error}</p>}

          {doneItems.length > 0 && (
            <>
              <BatchDashboardHeader items={doneItems} />
              <BatchFilters value={filters} onChange={setFilters} />
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {filtered.map((item) => (
                  <ContractCard
                    key={item.doc_id}
                    item={item}
                    onOpen={() => setSelected(item)}
                  />
                ))}
              </div>
              {filtered.length === 0 && (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  Ningún contrato coincide con los filtros.
                </p>
              )}
            </>
          )}
        </div>
      )}

      <ContractModal
        batchId={batchId ?? ""}
        item={selected}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

export default function BatchPage() {
  return (
    <Suspense>
      <BatchContent />
    </Suspense>
  );
}
