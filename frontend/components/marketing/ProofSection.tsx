import { Money } from "@/components/thesis/Money";
import { Reveal } from "./Reveal";

interface Stat {
  value: string;
  label: string;
}

const STATS: Stat[] = [
  { value: "1", label: "nulidad evitada" },
  { value: "23,3%", label: "clausulado desactualizado" },
  { value: "Cita", label: "en cada cifra" },
];

export function ProofSection() {
  return (
    <section
      id="prueba"
      className="scroll-mt-24 border-t border-n300/40 px-6 py-24 md:py-28"
    >
      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
        <Reveal>
          <div>
            <h2 className="font-display text-[clamp(2rem,4.5vw,3rem)] font-medium leading-[1.1] text-toga text-balance">
              El número que cambia la conversación.
            </h2>
            <p className="mt-3.5 max-w-md text-[15px] leading-relaxed text-body">
              No mostramos “análisis con IA”. Mostramos la exposición consolidada
              de la empresa cliente, con su fórmula determinista y su fuente
              citable.
            </p>
          </div>
        </Reveal>

        <Reveal delay={120}>
          <div className="relative overflow-hidden rounded-2xl border border-n300/60 bg-surface p-7 shadow-lift sm:p-8">
            <span className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-acento">
              <span className="size-1.5 rounded-full bg-acento" aria-hidden="true" />
              Exposición consolidada
            </span>
            <Money
              value={71175000}
              className="mt-3 block font-display text-[clamp(3rem,6vw,4.25rem)] font-medium leading-none tracking-tight text-toga tnum"
            />
            <div className="mt-7 grid grid-cols-3 divide-x divide-n300/60 border-t border-n300/60 pt-6">
              {STATS.map((s) => (
                <div key={s.label} className="px-4 first:pl-0">
                  <div className="font-display text-[26px] font-medium text-toga tnum">
                    {s.value}
                  </div>
                  <p className="mt-1 text-[13px] text-toga-300">{s.label}</p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
