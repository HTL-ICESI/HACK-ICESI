import { Check, FileSearch, ShieldCheck } from "lucide-react";

import { GlowBorder } from "./GlowBorder";
import { Reveal } from "./Reveal";

const MOTOR_1 = [
  "Extracción con cita y confianza",
  "Liquidación verificada: “✓ calculado”",
  "Riesgo de reclasificación (Ley 2466)",
];

const MOTOR_2 = [
  "Guardián del debido proceso en vivo",
  "Alerta de nulidad (art. 29 CN)",
  "Genera citación, acta y decisión",
];

function CheckItem({ children, dark }: { children: string; dark?: boolean }) {
  return (
    <li
      className={
        dark
          ? "flex items-center gap-2.5 text-sm text-lienzo"
          : "flex items-center gap-2.5 text-sm text-toga"
      }
    >
      <Check
        className={dark ? "size-4 shrink-0 text-[#E07A72]" : "size-4 shrink-0 text-ok"}
        aria-hidden="true"
      />
      {children}
    </li>
  );
}

export function MotorsSection() {
  return (
    <section id="motores" className="scroll-mt-24 px-6 py-24 md:py-28">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <div className="max-w-xl">
            <h2 className="font-display text-[clamp(2rem,4.5vw,3rem)] font-medium leading-[1.1] text-toga text-balance">
              Donde la firma gana o pierde dinero.
            </h2>
            <p className="mt-3.5 text-[15px] leading-relaxed text-body">
              Un cerebro de derecho laboral colombiano vivo. Lo determinista lo
              garantiza el código; el modelo solo redacta. Sin fuente, no se
              afirma.
            </p>
          </div>
        </Reveal>

        <div className="mt-9 grid gap-6 md:grid-cols-2">
          {/* Motor 1 — Compliance Vivo (clara) */}
          <Reveal className="h-full">
            <div className="h-full rounded-2xl border border-n300/60 bg-surface p-7 shadow-lift transition-[transform,box-shadow,border-color] duration-200 ease-out hover:-translate-y-1 hover:border-acento/30 hover:shadow-bezel-hover">
              <span className="flex size-12 items-center justify-center rounded-xl bg-acento-soft text-acento">
                <FileSearch className="size-5" aria-hidden="true" />
              </span>
              <h3 className="mt-4 font-display text-[24px] font-medium text-toga">
                Compliance Vivo
              </h3>
              <p className="mt-2 text-[15px] leading-relaxed text-body">
                Detecta cláusulas desactualizadas frente a la norma, verifica la
                liquidación con cálculo determinista y cuantifica la sanción en
                pesos. Genera el otrosí.
              </p>
              <ul className="mt-5 space-y-2.5">
                {MOTOR_1.map((item) => (
                  <CheckItem key={item}>{item}</CheckItem>
                ))}
              </ul>
            </div>
          </Reveal>

          {/* Motor 2 — Disciplinario Blindado (la joya) */}
          <Reveal delay={90} className="h-full">
            <GlowBorder
              className="h-full shadow-lift transition-transform duration-200 ease-out hover:-translate-y-1"
              innerClassName="relative h-full overflow-hidden bg-carbon p-7 text-lienzo"
            >
              <div
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(70%_60%_at_85%_0%,rgba(128,24,23,0.28),transparent_65%)]"
              />
              <div className="relative">
                <span className="flex size-12 items-center justify-center rounded-xl bg-white/10 text-[#E07A72]">
                  <ShieldCheck className="size-5" aria-hidden="true" />
                </span>
                <div className="mt-4 flex items-center gap-2.5">
                  <h3 className="font-display text-[24px] font-medium text-lienzo">
                    Disciplinario Blindado
                  </h3>
                  <span className="rounded bg-[#E07A72] px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-toga">
                    la joya
                  </span>
                </div>
                <p className="mt-2 text-[15px] leading-relaxed text-lienzo/75">
                  Conduce la diligencia de descargos y avisa en vivo si se va a
                  cometer una nulidad, antes de que ocurra. Bloquea la decisión
                  si falta debido proceso.
                </p>
                <ul className="mt-5 space-y-2.5">
                  {MOTOR_2.map((item) => (
                    <CheckItem key={item} dark>
                      {item}
                    </CheckItem>
                  ))}
                </ul>
              </div>
            </GlowBorder>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
