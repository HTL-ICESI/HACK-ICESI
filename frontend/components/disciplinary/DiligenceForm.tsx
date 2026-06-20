"use client";

import { useState } from "react";
import { Check, Search, Star } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { usePersona } from "@/components/shell/persona-context";
import { useBatchWorkers } from "@/hooks/useBatchWorkers";
import { RISK_STYLE } from "@/components/batch/risk";
import type { BatchItem } from "@/lib/types";
import { RitLoader, type RitRef } from "./RitLoader";

export interface DiligenceMeta {
  worker: string;
  falta: string;
  rit: string;
  doc_id?: string;
}

export function DiligenceForm({
  onStart,
}: {
  onStart: (meta: DiligenceMeta) => void;
}) {
  const { company } = usePersona();
  const { workers } = useBatchWorkers();

  const [worker, setWorker] = useState("");
  const [selectedDocId, setSelectedDocId] = useState<string | undefined>();
  const [falta, setFalta] = useState("");
  const [rit, setRit] = useState<RitRef | null>(null);
  const [open, setOpen] = useState(false);
  const [touched, setTouched] = useState<{ worker?: boolean; falta?: boolean }>({});

  const valid = worker.trim().length > 0 && falta.trim().length > 0;

  // Sugerencias del último lote, filtradas por lo que el abogado va escribiendo.
  const q = worker.trim().toLowerCase();
  const matches = workers.filter(
    (w) => !q || w.summary!.worker_name.toLowerCase().includes(q),
  );
  const showSuggestions = open && matches.length > 0;

  function selectWorker(item: BatchItem) {
    setWorker(item.summary!.worker_name);
    setSelectedDocId(item.doc_id);
    setOpen(false);
  }

  // Rellena la diligencia con un caso de muestra (igual que el botón demo del login).
  // Usa un trabajador real del lote si lo hay; si no, un nombre de ejemplo.
  function fillDemo() {
    const sample = workers[0];
    if (sample?.summary) {
      setWorker(sample.summary.worker_name);
      setSelectedDocId(sample.doc_id);
    } else {
      setWorker("Juan David Ospino Martínez");
      setSelectedDocId(undefined);
    }
    setFalta(
      "Ausencia injustificada al puesto de trabajo durante tres (3) días consecutivos, en presunta infracción del Artículo 42 del RIT.",
    );
    setOpen(false);
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (valid)
          onStart({ worker, falta, rit: rit?.filename ?? "RIT", doc_id: selectedDocId });
      }}
      className="space-y-5 rounded-2xl border border-n300/60 bg-card p-5 shadow-hairline"
    >
      {/* Botón demo: rellena la diligencia con un caso de muestra. */}
      <div className="flex justify-end">
        <button
          type="button"
          title="Rellenar diligencia de muestra"
          onClick={fillDemo}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-muted-foreground transition-colors hover:bg-n100 hover:text-toga"
        >
          <Star className="size-3" />
          demo
        </button>
      </div>

      {/* Trabajador: autocompletar sobre los contratos ya analizados de la empresa */}
      <div className="space-y-1.5">
        <label htmlFor="worker" className="text-sm font-medium text-toga">
          Trabajador
        </label>
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            id="worker"
            value={worker}
            onChange={(e) => {
              setWorker(e.target.value);
              setSelectedDocId(undefined);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => {
              setTouched((t) => ({ ...t, worker: true }));
              // Demora el cierre para permitir el click en una sugerencia.
              setTimeout(() => setOpen(false), 120);
            }}
            placeholder={
              workers.length > 0
                ? "Busca o escribe el nombre del trabajador"
                : "Nombre del trabajador"
            }
            className="pl-9"
            autoComplete="off"
            aria-invalid={touched.worker && !worker.trim() ? true : undefined}
          />

          {showSuggestions && (
            <ul className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-lg border border-n300/60 bg-card p-1 shadow-bezel">
              {matches.map((item) => {
                const s = item.summary!;
                const style = RISK_STYLE[s.risk_level];
                const isSelected = item.doc_id === selectedDocId;
                return (
                  <li key={item.doc_id}>
                    <button
                      type="button"
                      // onMouseDown corre antes que el onBlur del input.
                      onMouseDown={(e) => {
                        e.preventDefault();
                        selectWorker(item);
                      }}
                      className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm transition-colors hover:bg-acento/5"
                    >
                      <span
                        className={`size-1.5 shrink-0 rounded-full ${style.dot}`}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1 truncate text-toga">
                        {s.worker_name}
                      </span>
                      <span className="shrink-0 text-[11px] text-muted-foreground">
                        {style.label}
                      </span>
                      {isSelected && (
                        <Check className="size-3.5 shrink-0 text-acento" aria-hidden />
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        {touched.worker && !worker.trim() ? (
          <p className="text-xs text-risk-fg">Ingresa el nombre del trabajador.</p>
        ) : (
          <p className="text-xs text-muted-foreground">
            {workers.length > 0
              ? "Selecciona un trabajador analizado o escribe el nombre."
              : "Como aparece en el contrato."}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <label htmlFor="falta" className="text-sm font-medium text-toga">
          Falta imputada
        </label>
        <Textarea
          id="falta"
          value={falta}
          onChange={(e) => setFalta(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, falta: true }))}
          placeholder="Describe la presunta falta al reglamento interno de trabajo"
          aria-invalid={touched.falta && !falta.trim() ? true : undefined}
        />
        {touched.falta && !falta.trim() ? (
          <p className="text-xs text-risk-fg">Describe la falta imputada.</p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Conducta y norma del RIT presuntamente infringida.
          </p>
        )}
      </div>

      <RitLoader companyId={company.id} onChange={setRit} />

      <Button type="submit" disabled={!valid}>
        Iniciar diligencia
      </Button>
    </form>
  );
}
