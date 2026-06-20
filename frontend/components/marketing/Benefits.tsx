import { Code2, FileText, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Reveal } from "./Reveal";

interface Principle {
  icon: LucideIcon;
  title: string;
  body: string;
}

// Los principios de la tesis (mandan sobre cada pantalla).
const PRINCIPLES: Principle[] = [
  {
    icon: FileText,
    title: "Sin fuente, no se afirma",
    body: "Todo número abre su cita textual, con la norma y la confianza de lectura. Trazabilidad determinística.",
  },
  {
    icon: Code2,
    title: "El código garantiza, el modelo redacta",
    body: "Liquidación y exposición las calcula código determinista, auditado con tests. El LLM solo redacta el borrador.",
  },
  {
    icon: ShieldCheck,
    title: "La honestidad es valor, no falla",
    body: "“Requiere revisión humana” y “bloqueado” se muestran sin esconder. El bloqueo de la decisión es la demostración de valor.",
  },
];

export function Benefits() {
  const featured = PRINCIPLES[0];
  const FeaturedIcon = featured.icon;
  const supporting = PRINCIPLES.slice(1);

  return (
    <section id="beneficios" className="scroll-mt-24 bg-toga px-6 py-24 text-lienzo md:py-28">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <h2 className="max-w-xl font-display text-[clamp(2rem,4.5vw,3rem)] font-medium leading-[1.12] text-lienzo">
            Vendemos riesgo evitado, no eficiencia.
          </h2>
          <p className="mt-3.5 max-w-xl text-[15px] leading-relaxed text-lienzo/70">
            El abogado valida y firma; el sistema es asistente, no sustituto.
            Estos principios mandan sobre cada pantalla.
          </p>
        </Reveal>

        {/* Asimétrico a propósito: la tesis va destacada (fila ancha), los dos
            principios de soporte la acompañan. Rompe el grid de 3 tarjetas iguales. */}
        <div className="mt-11 space-y-9">
          <Reveal>
            <div className="flex flex-col gap-5 border-b border-white/10 pb-9 sm:flex-row sm:items-start sm:gap-6">
              <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-white/10 text-[#A1D4D2]">
                <FeaturedIcon className="size-6" aria-hidden="true" />
              </span>
              <div className="max-w-2xl">
                <h3 className="font-display text-[clamp(1.375rem,2.4vw,1.75rem)] font-medium leading-snug text-lienzo">
                  {featured.title}
                </h3>
                <p className="mt-2.5 text-[15px] leading-relaxed text-lienzo/70">
                  {featured.body}
                </p>
              </div>
            </div>
          </Reveal>

          <div className="grid gap-8 sm:grid-cols-2">
            {supporting.map((p, i) => {
              const Icon = p.icon;
              return (
                <Reveal key={p.title} delay={i * 70}>
                  <span className="flex size-10 items-center justify-center rounded-xl bg-white/10 text-[#A1D4D2]">
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="mt-4 text-[17px] font-semibold text-lienzo">
                    {p.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-lienzo/70">
                    {p.body}
                  </p>
                </Reveal>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
