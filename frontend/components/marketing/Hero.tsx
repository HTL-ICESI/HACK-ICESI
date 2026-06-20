import { CtaButton } from "./CtaButton";
import { ProductMock } from "./ProductMock";
import { Reveal } from "./Reveal";

export function Hero() {
  return (
    <section className="relative px-6 pb-20 pt-40 md:pb-28 md:pt-48">
      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
        <div>
          <Reveal>
            <span className="inline-flex items-center gap-2 rounded-full border border-acento/20 bg-acento-soft px-3.5 py-1.5 font-mono text-[13px] uppercase tracking-[0.16em] text-acento">
              <span className="size-1.5 rounded-full bg-acento" aria-hidden="true" />
              Compliance laboral vivo
            </span>
          </Reveal>

          <Reveal delay={80}>
            <h1 className="mt-6 text-balance font-display text-[clamp(3rem,7vw,5.25rem)] font-medium leading-[1.01] tracking-[-0.025em] text-toga">
              Ve el riesgo antes de que cueste.
            </h1>
          </Reveal>

          <Reveal delay={160}>
            <p className="mt-6 max-w-xl text-xl leading-relaxed text-body">
              Lo desactualizado, en pesos. La nulidad, frenada antes de que
              ocurra. El cerebro de derecho laboral colombiano para tu firma.
            </p>
          </Reveal>

          <Reveal delay={240}>
            <div className="mt-8 flex flex-wrap gap-3">
              <CtaButton href="/login" variant="primary">
                Ver el demo
              </CtaButton>
              <CtaButton href="#motores" variant="secondary">
                Cómo funciona
              </CtaButton>
            </div>
          </Reveal>

          <Reveal delay={320}>
            <p className="mt-7 font-mono text-xs text-toga-300">
              CST · Ley 2101/2021 · Ley 2466/2025 · CSJ Sala Laboral
            </p>
          </Reveal>
        </div>

        <Reveal delay={200} className="lg:pl-4">
          <ProductMock />
        </Reveal>
      </div>
    </section>
  );
}
