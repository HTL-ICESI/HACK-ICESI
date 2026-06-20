"use client";

import { Menu } from "lucide-react";

import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { CompanySelector } from "./CompanySelector";
import { PersonaSwitch } from "./PersonaSwitch";

interface TopbarProps {
  onMenu: () => void;
}

/**
 * Barra superior (F1). DESIGN.md §4: el switch de persona va arriba.
 * Acompañado del selector de empresa y el avatar del usuario (auth mock).
 */
export function Topbar({ onMenu }: TopbarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-n300/60 bg-surface/90 px-4 backdrop-blur md:px-6">
      <button
        aria-label="Abrir menú"
        onClick={onMenu}
        className="flex size-11 items-center justify-center rounded-md text-foreground hover:bg-n100 md:hidden"
      >
        <Menu className="size-5" />
      </button>

      <div className="ml-auto flex items-center gap-2 md:gap-3">
        <div className="hidden sm:block">
          <PersonaSwitch />
        </div>
        <CompanySelector />
        <ThemeToggle />
      </div>
    </header>
  );
}
