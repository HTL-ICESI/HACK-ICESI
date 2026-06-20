import { CtaButton } from "./CtaButton";
import { ProductMock } from "./ProductMock";
import { Reveal } from "./Reveal";

export function Hero() {
  return (
    <section className="relative overflow-hidden px-6 pb-20 pt-36 md:pb-28 md:pt-44">
      {/* Glow índigo de marca (momento hero, DESIGN.md §6) */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(80%_55%_at_82%_-5%,rgba(128,24,23,0.10),transparent_60%)]"
      />

      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
        <div>
          <Reveal>
            <span className="inline-flex rounded-full bg-acento-soft px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-acento">
              Compliance laboral vivo
            </span>
          </Reveal>

          <Reveal delay={80}>
            <h1 className="mt-5 text-balance font-display text-[clamp(2.5rem,6vw,4.5rem)] font-medium leading-[1.04] tracking-tight text-toga">
              Ve el riesgo antes de que cueste.
            </h1>
          </Reveal>

          <Reveal delay={160}>
            <p className="mt-5 max-w-lg text-lg leading-relaxed text-body">
              Lo desactualizado, en pesos. La nulidad, frenada antes de que
              ocurra. El cerebro de derecho laboral colombiano para tu firma.
            </p>
          </Reveal>

          <Reveal delay={240}>
            <div className="mt-8 flex flex-wrap gap-3">
              <CtaButton href="/login" variant="primary">
                Iniciar sesión
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
