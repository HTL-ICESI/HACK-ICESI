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
      className="scroll-mt-24 border-t border-n300/60 bg-surface px-6 py-24 md:py-28"
    >
      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
        <Reveal>
          <div>
            <h2 className="font-display text-[clamp(2rem,4.5vw,3rem)] font-medium leading-[1.1] text-toga text-balance">
              El número que cambia la conversación.
            </h2>
            <p className="mt-3.5 max-w-md text-[15px] leading-relaxed text-body">
              No mostramos “análisis con IA”. Mostramos la exposición consolidada
              de la empresa cliente — con su fórmula determinista y su fuente
              citable.
            </p>
          </div>
        </Reveal>

        <Reveal delay={120}>
          <div>
            <Money
              value={71175000}
              className="font-display text-[clamp(3rem,6vw,4rem)] font-medium leading-none tracking-tight"
            />
            <div className="mt-7 grid grid-cols-3 gap-4">
              {STATS.map((s) => (
                <div key={s.label} className="border-l-2 border-acento-soft pl-3.5">
                  <div className="font-display text-[26px] font-medium text-toga tnum">
                    {s.value}
                  </div>
                  <p className="mt-1 text-[13px] text-toga-300">
                    {s.label}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
