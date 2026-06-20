"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

import { cn } from "@/lib/utils";

const THEME_KEY = "cl-theme";

/**
 * Interruptor de tema. Lee/escribe la clase `dark` en <html> (la preferencia la
 * persiste el mismo key que usa el script anti-FOUC). Renderiza un estado neutro
 * hasta montar para no romper la hidratación.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const [mounted, setMounted] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const next = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", next);
    try {
      window.localStorage.setItem(THEME_KEY, next ? "dark" : "light");
    } catch {
      // localStorage bloqueado (modo privado): el toggle sigue funcionando en sesión.
    }
    setDark(next);
  }

  const label = !mounted
    ? "Cambiar tema"
    : dark
      ? "Activar modo claro"
      : "Activar modo oscuro";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex size-9 items-center justify-center rounded-md text-foreground transition-colors hover:bg-n100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        className,
      )}
    >
      {mounted && dark ? (
        <Sun className="size-[18px]" aria-hidden="true" />
      ) : (
        <Moon className="size-[18px]" aria-hidden="true" />
      )}
    </button>
  );
}
