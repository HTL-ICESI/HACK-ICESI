import { Money } from "@/components/thesis/Money";
import { SourceChip } from "@/components/thesis/SourceChip";
import { StatusBadge } from "@/components/thesis/StatusBadge";
import { formatDate } from "@/lib/format";
import type { DocumentRecord, Field } from "@/lib/types";

// Sentinel para campos que el backend devuelve como null (datos operativos, no del contrato).
const ABSENT: Field<null> = { status: "not_found", value: null, source: null };

interface FieldRowProps {
  label: string;
  field: Field<unknown> | null;
  children: React.ReactNode;
  docText?: string | null;
  onGoToContract?: (span: { start: number; end: number }) => void;
}

function FieldRow({ label, field, children, docText, onGoToContract }: FieldRowProps) {
  const f = field ?? ABSENT;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-n300/50 py-2.5 last:border-b-0">
      <span className="w-36 shrink-0 text-sm text-muted-foreground">
        {label}
      </span>
      {/* Honestidad: si no se leyó con confianza, NO mostramos un valor inventado. */}
      {f.status === "ok" ? (
        <span className="text-sm font-medium text-toga">{children}</span>
      ) : (
        <span className="text-sm text-muted-foreground">Sin dato</span>
      )}
      <span className="ml-auto flex items-center gap-2">
        {f.status === "ok" && f.source && (
          <SourceChip
            source={f.source}
            label="contrato"
            docText={docText}
            onGoToContract={onGoToContract}
          />
        )}
        {f.status === "needs_human" && <StatusBadge kind="needs_human" />}
        {f.status === "not_found" && (
          <StatusBadge kind="needs_human" label="no encontrado" />
        )}
      </span>
    </div>
  );
}

const VINCULO: Record<string, string> = {
  termino_fijo: "Término fijo",
  termino_indefinido: "Término indefinido",
  obra_labor: "Obra o labor",
  prestacion_servicios: "Prestación de servicios",
};

function boolText(value: boolean | null): string {
  return value === true ? "Sí" : value === false ? "No" : "Sin dato";
}

interface ExtractedRecordProps {
  record: DocumentRecord;
  docText?: string | null;
  onGoToContract?: (span: { start: number; end: number }) => void;
}

export function ExtractedRecord({ record, docText, onGoToContract }: ExtractedRecordProps) {
  const r = record;
  const employerVal = r.employer?.value;
  const salaryVal = r.base_salary?.value;
  const row = (label: string, field: Field<unknown> | null, children: React.ReactNode) => (
    <FieldRow label={label} field={field} docText={docText} onGoToContract={onGoToContract}>
      {children}
    </FieldRow>
  );
  return (
    <div className="rounded-lg border border-n300/60 bg-card px-5 shadow-hairline">
      {row("Empleador", r.employer,
        <>{employerVal?.name}{employerVal?.nit ? ` · NIT ${employerVal.nit}` : ""}</>)}
      {row("Trabajador", r.empleado_nombre, r.empleado_nombre?.value)}
      {row("Documento", r.empleado_documento,
        <span className="font-mono">{r.empleado_documento?.value}</span>)}
      {row("Cargo", r.role, r.role?.value)}
      {row("Tipo de vínculo", r.vinculo_type,
        VINCULO[r.vinculo_type?.value ?? ""] ?? r.vinculo_type?.value)}
      {row("Salario base", r.base_salary,
        <>{salaryVal && <Money value={salaryVal.value} />}{" "}
        {salaryVal && <span className="text-xs text-muted-foreground">/ {salaryVal.periodicity}</span>}</>)}
      {row("Auxilio de transporte", r.auxilio_transporte,
        r.auxilio_transporte?.value && <Money value={r.auxilio_transporte.value.value} />)}
      {row("Salario variable", r.salario_variable,
        boolText((r.salario_variable?.value as boolean | null) ?? null))}
      {row("Inicio", r.start_date, formatDate(r.start_date?.value ?? null))}
      {row("Fin", r.end_date, formatDate(r.end_date?.value ?? null))}
      {row("Jornada", r.weekly_hours, <>{r.weekly_hours?.value} h/semana</>)}
      {row("Terminación pactada", r.termination_confirmed,
        boolText((r.termination_confirmed?.value as boolean | null) ?? null))}
      {row("Mora en seg. social", r.pago_ss_mora,
        boolText((r.pago_ss_mora?.value as boolean | null) ?? null))}
    </div>
  );
}
