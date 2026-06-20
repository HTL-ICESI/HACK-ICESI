"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

interface RevealProps {
  children: React.ReactNode;
  className?: string;
  /** Retardo escalonado en ms. */
  delay?: number;
}

/**
 * Entrada suave al entrar en viewport.
 * El contenido es VISIBLE en SSR/HTML estático (shown=true por defecto).
 * En el cliente, si el elemento no está aún en viewport al montar,
 * se resetea a oculto y el IntersectionObserver lo revela al entrar.
 * Así las páginas estáticas nunca quedan en blanco por hidratación tardía.
 */
export function Reveal({ children, className, delay = 0 }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  // true = visible en SSR/HTML estático; el cliente puede resetearlo para animar.
  const [shown, setShown] = useState(true);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return; // ya está shown=true

    // Si el elemento ya está en el viewport al montar, no ocultamos (evita flash).
    const rect = el.getBoundingClientRect();
    const inView = rect.top < window.innerHeight && rect.bottom > 0;
    if (inView) return;

    // Fuera del viewport: ocultamos y esperamos que entre.
    setShown(false);
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShown(true);
            io.disconnect();
          }
        }
      },
      { threshold: 0, rootMargin: "0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [delay]);

  return (
    <div
      ref={ref}
      style={shown ? undefined : { transitionDelay: `${delay}ms` }}
      className={cn(
        "transition-[opacity,transform,filter] duration-700 ease-snappy",
        shown
          ? "translate-y-0 opacity-100 blur-0"
          : "translate-y-6 opacity-0 blur-[2px]",
        className,
      )}
    >
      {children}
    </div>
  );
}
