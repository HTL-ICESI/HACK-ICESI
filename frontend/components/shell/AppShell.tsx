"use client";

import { useState } from "react";

import { PersonaProvider } from "./persona-context";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/**
 * Shell de la app (F1): sidebar carbón HG + topbar con switch de persona y
 * selector de empresa. Provee el contexto de persona/empresa a todo el árbol.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <PersonaProvider>
      <div className="flex min-h-[100dvh] bg-background">
        <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar onMenu={() => setMobileOpen(true)} />
          <main className="flex-1">{children}</main>
        </div>
      </div>
    </PersonaProvider>
  );
}
