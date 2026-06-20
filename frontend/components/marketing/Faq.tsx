import { ChevronDown } from "lucide-react";

import { Reveal } from "./Reveal";

interface QA {
  q: string;
  a: string;
}

// Las preguntas que hace quien decide (el jurado / el socio de la firma).
const FAQS: QA[] = [
  {
    q: "¿Qué pasa cuando la IA se equivoca?",
    a: "Cada lectura tiene un estado: “requiere revisión humana” frena el flujo y nunca inventa datos. Las cifras las calcula código determinista, no el modelo.",
  },
  {
    q: "¿Quién responde legalmente?",
    a: "El abogado valida, aprueba y firma. El sistema es un asistente que muestra el riesgo con su fuente. No sustituye el criterio jurídico.",
  },
  {
    q: "¿Por qué este enfoque técnico?",
    a: "Separamos lo determinista de lo generativo: el código garantiza cifras y veredictos auditables; el LLM solo redacta borradores marcados como “revisar”.",
  },
  {
    q: "¿Qué normas regulan la IA legal en Colombia hoy?",
    a: "El marco está en construcción; por eso el diseño prioriza trazabilidad, validación humana y registro de auditoría, coherente con los principios de IA responsable.",
  },
];

export function Faq() {
  return (
    <section
      id="faq"
      className="scroll-mt-24 border-t border-n300/40 px-6 py-24 md:py-28"
    >
      <div className="mx-auto max-w-3xl">
        <Reveal>
          <h2 className="font-display text-[clamp(1.875rem,4vw,2.5rem)] font-medium leading-[1.1] text-toga text-balance">
            Lo que pregunta quien decide.
          </h2>
        </Reveal>

        <Reveal delay={100}>
          <div className="mt-8 space-y-3">
            {FAQS.map((item) => (
              <details
                key={item.q}
                className="group rounded-xl border border-n300/60 bg-surface px-5 shadow-bezel transition-colors open:border-acento/30 hover:border-acento/30"
              >
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-[17px] font-medium text-toga [&::-webkit-details-marker]:hidden">
                  {item.q}
                  <ChevronDown
                    className="size-5 shrink-0 text-muted-foreground transition-transform duration-200 ease-out group-open:rotate-180 group-open:text-acento"
                    aria-hidden="true"
                  />
                </summary>
                <p className="max-w-prose animate-in fade-in slide-in-from-top-1 pb-5 text-[15px] leading-relaxed text-body duration-200">
                  {item.a}
                </p>
              </details>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}
