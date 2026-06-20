import Link from "next/link";
import { Play } from "lucide-react";

import { Reveal } from "./Reveal";

/**
 * Sección de video del producto (va justo después del Hero). Placeholder: marco 16:9 en
 * Carbón HG rayado con botón de play. El play NO es un control muerto: abre el demo en vivo.
 * Cuando exista el video real, se reemplaza por <video poster=...> y el play lo reproduce.
 */
export function VideoDemo() {
  return (
    <section id="video" className="scroll-mt-24 px-6 pb-24 pt-6 md:pb-28">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <div className="max-w-xl">
            <h2 className="font-display text-[clamp(2rem,4.5vw,3rem)] font-medium leading-[1.1] text-toga text-balance">
              Míralo en acción.
            </h2>
            <p className="mt-3.5 text-[15px] leading-relaxed text-body">
              Del contrato al número mágico, y de la diligencia a la nulidad
              frenada — en 90 segundos.
            </p>
          </div>
        </Reveal>

        <Reveal delay={120}>
          <Link
            href="/login"
            aria-label="Reproducir el recorrido del producto y acceder al demo en vivo"
            className="group relative mt-9 block aspect-video overflow-hidden rounded-2xl bg-toga shadow-bezel transition-transform duration-200 ease-out active:scale-[0.99] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acento focus-visible:ring-offset-2 focus-visible:ring-offset-lienzo"
          >
            {/* Textura rayada de marca */}
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 bg-[repeating-linear-gradient(135deg,rgba(255,255,255,0.04)_0_12px,transparent_12px_24px)]"
            />
            {/* Halo rojo HG */}
            <span
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_70%_at_50%_0%,rgba(128,24,23,0.22),transparent_65%)]"
            />

            {/* Botón de play (foco) */}
            <span className="absolute inset-0 flex items-center justify-center">
              <span className="flex size-[76px] items-center justify-center rounded-full bg-lienzo text-toga shadow-bezel transition-transform duration-200 ease-out [@media(hover:hover)]:group-hover:scale-105">
                <Play className="size-7 translate-x-0.5 fill-toga" aria-hidden="true" />
              </span>
            </span>

            <span className="absolute bottom-4 left-5 font-mono text-[12px] text-lienzo/75">
              [ demo del producto · 90s ]
            </span>
            <span className="absolute right-5 top-4 inline-flex items-center gap-1.5 font-mono text-[11px] text-lienzo/60">
              <span className="size-[7px] rounded-full bg-[#A1D4D2]" aria-hidden="true" />
              Cerebro Laboral
            </span>
          </Link>
        </Reveal>

        <Reveal delay={180}>
          <p className="mt-4 font-mono text-[12px] text-toga-300">
            Video próximamente — por ahora, el play abre el demo interactivo.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
