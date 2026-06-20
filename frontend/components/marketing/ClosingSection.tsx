import { CtaButton } from "./CtaButton";
import { Reveal } from "./Reveal";

export function ClosingSection() {
  return (
    <section
      id="demo"
      className="scroll-mt-24 border-t border-n300/40 px-6 py-24 md:py-28"
    >
      <div className="mx-auto max-w-3xl text-center">
        <Reveal>
          <h2 className="text-balance font-display text-[clamp(2.25rem,5vw,3.25rem)] font-medium leading-[1.06] tracking-tight text-toga">
            Ve el riesgo antes de que cueste.
          </h2>
        </Reveal>
        <Reveal delay={100}>
          <p className="mt-3.5 text-[17px] text-muted-foreground">
            WorkLab, una solución de HG Hurtado Gandini.
          </p>
        </Reveal>
        <Reveal delay={150}>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <CtaButton href="/login" variant="primary">
              Ver el demo
            </CtaButton>
            <CtaButton href="/equipo" variant="secondary">
              Hablar con el equipo
            </CtaButton>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
