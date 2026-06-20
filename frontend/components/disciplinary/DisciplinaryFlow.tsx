"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Check, Plus, ShieldAlert, Trash2 } from "lucide-react";

import { usePersona } from "@/components/shell/persona-context";
import { EmptyState } from "@/components/common/EmptyState";
import {
  addCase,
  loadCases,
  removeCase,
  setCasePhone,
  setWorkerPhone,
  workerPhone,
  type DiscCase,
} from "@/lib/disciplinary-cases";
import { DiligenceForm, type DiligenceMeta } from "./DiligenceForm";
import { DescargosPipeline } from "./DescargosPipeline";

type View = { kind: "list" } | { kind: "new" } | { kind: "case"; id: string };

export function DisciplinaryFlow() {
  const { company } = usePersona();
  const [cases, setCases] = useState<DiscCase[]>([]);
  const [view, setView] = useState<View>({ kind: "list" });

  // localStorage es client-only → cargar tras montar / cambiar de empresa.
  useEffect(() => {
    setCases(loadCases(company.id));
    setView({ kind: "list" });
  }, [company.id]);

  const active =
    view.kind === "case" ? cases.find((c) => c.id === view.id) ?? null : null;

  function createCase(meta: DiligenceMeta) {
    const phone = workerPhone(company.id, meta.doc_id ?? meta.worker);
    const c = addCase(company.id, meta, phone);
    setCases(loadCases(company.id));
    setView({ kind: "case", id: c.id });
  }

  function deleteCase(id: string) {
    removeCase(company.id, id);
    setCases(loadCases(company.id));
  }

  // ── Vista: caso activo ──────────────────────────────────────────────────────
  if (view.kind === "case" && active) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8 md:py-10">
        <button
          onClick={() => setView({ kind: "list" })}
          className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-toga"
        >
          <ArrowLeft className="size-4" />
          Casos disciplinarios
        </button>

        <div className="mb-6 flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-2xl border border-n300/60 bg-card px-5 py-3 shadow-hairline">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-toga text-lienzo">
            <Check className="size-3.5" aria-hidden />
          </span>
          <span className="text-sm font-medium text-toga">{active.worker}</span>
          <span className="text-n300" aria-hidden>·</span>
          <span className="min-w-0 truncate text-sm text-muted-foreground">{active.falta}</span>
          <span className="font-mono text-xs text-muted-foreground">RIT {active.rit}</span>
        </div>

        <DescargosPipeline
          meta={active}
          companyName={company.name}
          telefono={active.telefono}
          onTelefono={(phone) => {
            setWorkerPhone(company.id, active.doc_id ?? active.worker, phone);
            setCasePhone(company.id, active.id, phone);
            setCases(loadCases(company.id));
          }}
        />
      </div>
    );
  }

  // ── Vista: nuevo caso ───────────────────────────────────────────────────────
  if (view.kind === "new") {
    return (
      <div className="mx-auto max-w-6xl px-6 py-8 md:py-10">
        <button
          onClick={() => setView({ kind: "list" })}
          className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-toga"
        >
          <ArrowLeft className="size-4" />
          Casos disciplinarios
        </button>
        <div className="max-w-xl">
          <div className="mb-3 flex items-center gap-3">
            <span className="flex size-8 items-center justify-center rounded-lg bg-acento-soft text-acento">
              <Check className="size-4" aria-hidden />
            </span>
            <h2 className="font-display text-lg font-medium text-toga">Nuevo caso disciplinario</h2>
          </div>
          <DiligenceForm onStart={createCase} />
        </div>
      </div>
    );
  }

  // ── Vista: dashboard / lista ────────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-6xl px-6 py-8 md:py-10">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <h1 className="font-display text-3xl font-medium text-toga">Disciplinario Blindado</h1>
          <p className="mt-1 text-[15px] text-muted-foreground">
            Cita por WhatsApp con evidencia, toma los descargos por llamada grabada y contrasta
            la defensa — con el Guardián frenando la nulidad en vivo.
          </p>
        </div>
        <button
          onClick={() => setView({ kind: "new" })}
          className="mt-1 inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-acento px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-acento/90"
        >
          <Plus className="size-4" aria-hidden />
          Nuevo caso
        </button>
      </header>

      {cases.length === 0 ? (
        <EmptyState
          icon={ShieldAlert}
          title="Sin casos disciplinarios abiertos"
          hint="Abre un caso para citar al trabajador y conducir la diligencia de descargos."
        />
      ) : (
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {cases.map((c) => (
            <div
              key={c.id}
              className="group relative rounded-lg border border-n300/60 bg-card p-3 text-left shadow-hairline transition-colors hover:border-acento/40"
            >
              <button
                onClick={() => setView({ kind: "case", id: c.id })}
                className="block w-full text-left"
              >
                <div className="flex items-center gap-2">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-acento-soft font-mono text-[10px] font-medium text-acento">
                    {c.worker.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase()}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-medium text-toga">{c.worker}</p>
                    <p className="font-mono text-[10px] text-muted-foreground">{c.telefono}</p>
                  </div>
                </div>
                <p className="mt-2 line-clamp-1 text-xs text-muted-foreground">{c.falta}</p>
                <p className="mt-2 border-t border-n300/50 pt-2 text-[10px] text-muted-foreground">
                  Abierto el{" "}
                  {new Date(c.createdAt).toLocaleDateString("es-CO", {
                    day: "numeric",
                    month: "short",
                  })}
                </p>
              </button>
              <button
                onClick={() => deleteCase(c.id)}
                aria-label="Eliminar caso"
                className="absolute right-2.5 top-2.5 rounded-md p-1 text-muted-foreground opacity-0 transition-opacity hover:bg-risk-soft hover:text-risk-fg group-hover:opacity-100"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
