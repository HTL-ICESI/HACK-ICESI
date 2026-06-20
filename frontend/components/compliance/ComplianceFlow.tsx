"use client";

import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { Money } from "@/components/thesis/Money";
import { StatusBadge } from "@/components/thesis/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  analyzeCompliance,
  computeLiquidation,
  extract,
  generateRemediation,
  ingest,
} from "@/lib/api";
import type {
  ComplianceResponse,
  ExtractResponse,
  IngestResponse,
  LiquidationRequest,
  LiquidationResponse,
  RemediationResponse,
} from "@/lib/types";
import { Dropzone } from "./Dropzone";
import { ExtractedRecord } from "./ExtractedRecord";
import { GapsList } from "./GapsList";
import { LiquidationTable } from "./LiquidationTable";
import { RemediationPanel } from "./RemediationPanel";
import { RiskDot, RiskSemaphore } from "./RiskSemaphore";
import { StepSection } from "./StepSection";

// Datos operativos del caso que no vienen del contrato (en producción los da nómina).
const CASE = {
  days_worked: 66,
  promedio_variable: 676784.614,
  dias_pendientes_vacaciones: 9,
  termination_cause: "renuncia" as const,
};

// Arma el request real de M4 desde el record extraído + los datos del caso.
function liquidationRequest(ext: ExtractResponse): LiquidationRequest {
  const r = ext.record;
  const aux =
    r.auxilio_transporte.status === "ok" && r.auxilio_transporte.value
      ? r.auxilio_transporte.value.value
      : 0;
  return {
    doc_id: ext.doc_id,
    monthly_salary: r.base_salary.value.value,
    days_worked: CASE.days_worked,
    vinculo_type: r.vinculo_type.value,
    promedio_variable: CASE.promedio_variable,
    auxilio_transporte: aux,
    dias_pendientes_vacaciones: CASE.dias_pendientes_vacaciones,
    termination_cause: CASE.termination_cause,
  };
}

const NEXT_LABEL: Record<number, string> = {
  1: "Extraer datos con su fuente",
  2: "Detectar riesgos",
  3: "Verificar liquidación",
  4: "Generar subsanación",
};

// "Recibo" colapsado por estado de ingesta.
const INGEST_SUMMARY: Record<IngestResponse["status"], React.ReactNode> = {
  digital: <StatusBadge kind="calculado" label="digital" />,
  ocr: <StatusBadge kind="info" label="OCR" />,
  needs_human: <StatusBadge kind="needs_human" />,
};

export function ComplianceFlow() {
  const [stage, setStage] = useState(0);
  const [openStep, setOpenStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ing, setIng] = useState<IngestResponse | null>(null);
  const [ext, setExt] = useState<ExtractResponse | null>(null);
  const [comp, setComp] = useState<ComplianceResponse | null>(null);
  const [liq, setLiq] = useState<LiquidationResponse | null>(null);
  const [rem, setRem] = useState<RemediationResponse | null>(null);

  const halted = ing?.status === "needs_human";

  // Acordeón de un solo abierto: clic en un encabezado abre ese paso. No se
  // permite colapsar todo — evita la pantalla en blanco de solo "recibos".
  const toggle = (n: number) => setOpenStep(n);

  async function runIngest(file?: File) {
    setLoading(true);
    setError(null);
    try {
      const res = await ingest(file);
      setIng(res);
      setStage(1);
      setOpenStep(1);
    } catch {
      setError(
        "No pudimos procesar el documento. Revisa la conexión e inténtalo de nuevo.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function next() {
    setLoading(true);
    setError(null);
    try {
      if (stage === 1 && ing) {
        setExt(await extract(ing.doc_id, ing.text));
        setStage(2);
        setOpenStep(2);
      } else if (stage === 2 && ext) {
        setComp(await analyzeCompliance(ext.doc_id, ext.record));
        setStage(3);
        setOpenStep(3);
      } else if (stage === 3 && ext) {
        setLiq(await computeLiquidation(liquidationRequest(ext)));
        setStage(4);
        setOpenStep(4);
      } else if (stage === 4 && comp && ext) {
        setRem(await generateRemediation(ext.doc_id, comp.gaps[0], liq, comp.gaps[0].remedy_type, ext.record));
        setStage(5);
        setOpenStep(5);
      }
    } catch {
      setError(
        "No pudimos completar este paso. Revisa la conexión e inténtalo de nuevo.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8 md:py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl font-medium text-toga">
          Compliance Vivo
        </h1>
        <p className="mt-1 text-[15px] text-muted-foreground">
          Sube un contrato y míralo analizado, arreglado y cuantificado — paso a
          paso, con su fuente.
        </p>
      </header>

      <div className="space-y-2">
        <StepSection
          n={1}
          title="Cargar documento"
          done={stage >= 1}
          summary={ing ? INGEST_SUMMARY[ing.status] : undefined}
          open={openStep === 1}
          onToggle={stage >= 1 ? () => toggle(1) : undefined}
        >
          <Dropzone
            onLoad={runIngest}
            loading={loading && stage === 0}
            result={ing}
          />
        </StepSection>

        {stage >= 2 && ext && (
          <StepSection
            n={2}
            title="Datos extraídos"
            done={stage >= 2}
            summary={
              <span className="font-sans text-sm text-muted-foreground">
                {Object.keys(ext.record).length} campos · con fuente
              </span>
            }
            open={openStep === 2}
            onToggle={() => toggle(2)}
          >
            <ExtractedRecord record={ext.record} />
          </StepSection>
        )}

        {stage >= 3 && comp && (
          <StepSection
            n={3}
            title="Riesgos detectados"
            done={stage >= 3}
            summary={<RiskDot summary={comp.summary} />}
            open={openStep === 3}
            onToggle={() => toggle(3)}
          >
            <div className="space-y-4">
              <RiskSemaphore summary={comp.summary} />
              <GapsList gaps={comp.gaps} />
            </div>
          </StepSection>
        )}

        {stage >= 4 && liq && (
          <StepSection
            n={4}
            title="Verificación de liquidación"
            done={stage >= 4}
            badge={<StatusBadge kind="calculado" />}
            summary={
              <span className="flex items-center gap-2">
                <Money value={liq.items.total} className="text-sm font-medium" />
                <StatusBadge kind="calculado" />
              </span>
            }
            open={openStep === 4}
            onToggle={() => toggle(4)}
          >
            <LiquidationTable
              data={liq}
              request={ext ? liquidationRequest(ext) : undefined}
            />
          </StepSection>
        )}

        {stage >= 5 && rem && (
          <StepSection
            n={5}
            title="Subsanación"
            done
            badge={<StatusBadge kind="revisar" />}
            summary={<StatusBadge kind="revisar" />}
            open={openStep === 5}
            onToggle={() => toggle(5)}
          >
            <RemediationPanel data={rem} />
          </StepSection>
        )}

        {stage >= 1 && stage < 5 && !halted && !error && (
          <div className="ml-10 pt-2">
            <Button onClick={next} disabled={loading} aria-busy={loading}>
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  {NEXT_LABEL[stage]}…
                </>
              ) : (
                <>
                  {NEXT_LABEL[stage]}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </>
              )}
            </Button>
          </div>
        )}

        {error && !loading && (
          <div className="ml-10 pt-2">
            <ErrorState
              title="No pudimos completar este paso"
              message={error}
              onRetry={ing ? next : runIngest}
            />
          </div>
        )}

        {halted && (
          <div className="ml-10 rounded-lg border border-warn/30 bg-warn-soft p-4 text-sm text-warn-fg">
            El documento requiere revisión humana antes de continuar. No se
            procesa automáticamente.
          </div>
        )}
      </div>
    </div>
  );
}
