"use client";

import { useState } from "react";
import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { cn } from "@/lib/utils";

interface NavLink {
  href: string;
  label: string;
}

const LINKS: NavLink[] = [
  { href: "#motores", label: "Producto" },
  { href: "#video", label: "Cómo funciona" },
  { href: "/compliance", label: "Para abogados" },
  { href: "/equipo", label: "Para RRHH" },
];

// Anclas (#) navegan en la página; rutas (/) usan Link para navegación instantánea.
function NavItem({
  href,
  label,
  onClick,
  className,
}: NavLink & { onClick?: () => void; className?: string }) {
  if (href.startsWith("/")) {
    return (
      <Link href={href} onClick={onClick} className={className}>
        {label}
      </Link>
    );
  }
  return (
    <a href={href} onClick={onClick} className={className}>
      {label}
    </a>
  );
}

export function MarketingNav() {
  const [open, setOpen] = useState(false);

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-50 flex justify-center px-4">
      <nav
        className="pointer-events-auto w-full max-w-5xl rounded-2xl border border-n300/60 bg-surface/80 px-4 py-2.5 shadow-bezel backdrop-blur-xl"
        aria-label="Navegación principal"
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
      >
        <div className="flex items-center justify-between gap-4">
          <Link href="/" aria-label="Inicio de WorkLab">
            <Logo imgClassName="h-11" />
          </Link>

          <div className="hidden items-center gap-7 md:flex">
            {LINKS.map((l) => (
              <NavItem
                key={l.href}
                href={l.href}
                label={l.label}
                className="text-sm font-medium text-body transition-colors hover:text-toga"
              />
            ))}
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/login"
              className="hidden text-sm font-medium text-toga transition-colors hover:text-acento md:inline-flex"
            >
              Iniciar sesión
            </Link>
            <Link
              href="/login"
              className="hidden rounded-full bg-primary px-5 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 sm:inline-flex"
            >
              Ver el demo
            </Link>

            {/* Hamburguesa morph (mobile) */}
            <button
              type="button"
              aria-label={open ? "Cerrar menú" : "Abrir menú"}
              aria-expanded={open}
              aria-controls="mobile-menu"
              onClick={() => setOpen((v) => !v)}
              className="relative flex size-9 items-center justify-center rounded-full hover:bg-n100 md:hidden"
            >
              <span
                className={cn(
                  "absolute h-0.5 w-5 rounded-full bg-toga transition-transform duration-200 ease-out",
                  open ? "rotate-45" : "-translate-y-1.5",
                )}
              />
              <span
                className={cn(
                  "absolute h-0.5 w-5 rounded-full bg-toga transition-transform duration-200 ease-out",
                  open ? "-rotate-45" : "translate-y-1.5",
                )}
              />
            </button>
          </div>
        </div>

        {/* Panel mobile — inert cuando está colapsado: no es enfocable ni
            llega al lector de pantalla mientras no esté abierto. */}
        <div
          id="mobile-menu"
          inert={!open}
          className={cn(
            "grid overflow-hidden transition-[grid-template-rows,opacity] duration-300 ease-fluid md:hidden",
            open ? "mt-3 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
          )}
        >
          <div className="min-h-0">
            <div className="flex flex-col gap-1 border-t border-n300/60 pt-3">
              {LINKS.map((l) => (
                <NavItem
                  key={l.href}
                  href={l.href}
                  label={l.label}
                  onClick={() => setOpen(false)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-body hover:bg-n100"
                />
              ))}
              <Link
                href="/login"
                onClick={() => setOpen(false)}
                className="mt-1 rounded-full bg-primary px-5 py-2.5 text-center text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Ver el demo
              </Link>
            </div>
          </div>
        </div>
      </nav>
    </div>
  );
}
