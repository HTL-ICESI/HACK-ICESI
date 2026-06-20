import { FileText, ShieldCheck } from "lucide-react";

import { Money } from "@/components/thesis/Money";
import { StatusBadge } from "@/components/thesis/StatusBadge";

/**
 * Mock estático del dashboard (money shot) para el hero. Reutiliza los primitivos reales
 * (Money, StatusBadge) para que la captura sea fiel al producto. La barra de composición usa
 * la rampa HG rojo/vino/gris (composición de datos, no semáforo).
 */
export function ProductMock() {
  return (
    <div className="relative">
      {/* Halo rojo HG detrás del mock. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -inset-6 -z-10 rounded-[2rem] bg-[radial-gradient(60%_60%_at_70%_30%,rgba(128,24,23,0.18),transparent_70%)] blur-2xl"
      />

      {/* Card del money shot */}
      <div className="rounded-2xl border border-n300/60 bg-surface p-6 shadow-bezel">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">
            Exposición en riesgo
          </span>
          <StatusBadge kind="calculado" />
        </div>

        <Money
          value={71175000}
          className="mt-2.5 font-display text-[2.75rem] leading-none tracking-tight"
        />

        {/* Barra de composición — rampa HG (cuánto aporta cada fuente de riesgo) */}
        <div
          className="mt-4 flex h-2.5 gap-0.5 overflow-hidden rounded-full bg-n100"
          aria-hidden="true"
        >
          <span className="w-[40%] bg-acento" />
          <span className="w-[30%] bg-[#743537]" />
          <span className="w-[20%] bg-toga-300" />
          <span className="w-[10%] bg-[#D8D0CC]" />
        </div>

        <div className="mt-3.5 flex flex-wrap items-center gap-2">
          <span className="chip-fuente">
            <FileText className="size-3" aria-hidden="true" />
            Ley 2101 · art. 3
          </span>
          <span className="text-xs text-toga-300">
            50 trabajadores en riesgo
          </span>
        </div>
      </div>

      {/* Card flotante: 1 nulidad evitada (Motor 2) */}
      <div className="absolute -bottom-6 -left-6 flex items-center gap-3 rounded-2xl border border-n300/60 bg-surface px-4 py-3.5 shadow-bezel">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-toga text-lienzo">
          <ShieldCheck className="size-[18px]" aria-hidden="true" />
        </span>
        <div>
          <div className="font-display text-xl font-medium leading-none text-toga">
            1 nulidad evitada
          </div>
          <div className="mt-1 text-xs text-toga-300">
            Guardián del debido proceso
          </div>
        </div>
      </div>
    </div>
  );
}
