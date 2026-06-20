import { formatCOP } from "@/lib/format";

interface Slice {
  label: string;
  pct: number;
  color: string;
}

/**
 * Desglose del número mágico: de qué se compone la exposición. Rampa monocroma
 * Rojo/vino/grises HG (composición de datos, NO semáforo).
 *
 * ⚠️ M6 (magic_number) aún no trae el desglose. Mientras tanto se deriva de la
 * exposición total con pesos fijos del caso de demostración. Cuando el backend
 * exponga `magic_number.breakdown[]`, se reemplaza por esa data.
 */
const SLICES: Slice[] = [
  { label: "Jornada por reliquidar", pct: 38, color: "#801817" },
  { label: "Reclasificación (Ley 2466)", pct: 27, color: "#743537" },
  { label: "Mora en seguridad social", pct: 22, color: "#776867" },
  { label: "Vacaciones y otros", pct: 13, color: "#D8D0CC" },
];

export function ExposureBreakdown({ total }: { total: number }) {
  return (
    <div>
      <div
        className="flex h-2.5 gap-0.5 overflow-hidden rounded-full bg-n100"
        role="img"
        aria-label="Composición de la exposición en riesgo"
      >
        {SLICES.map((s) => (
          <span
            key={s.label}
            className="h-full origin-left animate-grow-x"
            style={{ width: `${s.pct}%`, backgroundColor: s.color }}
          />
        ))}
      </div>

      <dl className="mt-4 grid grid-cols-1 gap-x-7 gap-y-2.5 sm:grid-cols-2">
        {SLICES.map((s) => (
          <div key={s.label} className="flex items-center gap-2.5">
            <span
              className="size-2.5 shrink-0 rounded-[3px]"
              style={{ backgroundColor: s.color }}
              aria-hidden="true"
            />
            <dt className="min-w-0 flex-1 truncate text-[13px] text-body">
              {s.label}
            </dt>
            <dd className="font-mono text-xs text-toga tnum">
              {formatCOP(Math.round((total * s.pct) / 100))}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
