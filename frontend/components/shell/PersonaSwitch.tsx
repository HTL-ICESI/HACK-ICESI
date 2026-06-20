"use client";

import { Scale, Users } from "lucide-react";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { type Persona, usePersona } from "./persona-context";

/**
 * Switch de persona — segmented control (DESIGN.md §4). Cambia densidad y vistas.
 */
export function PersonaSwitch() {
  const { persona, setPersona } = usePersona();
  return (
    <Tabs value={persona} onValueChange={(v) => setPersona(v as Persona)}>
      <TabsList>
        <TabsTrigger value="abogado">
          <Scale className="size-3.5" aria-hidden="true" />
          <span className="hidden sm:inline">Abogado · Firma</span>
          <span className="sm:hidden">Abogado</span>
        </TabsTrigger>
        <TabsTrigger value="rrhh">
          <Users className="size-3.5" aria-hidden="true" />
          <span className="hidden sm:inline">RRHH · Empresa</span>
          <span className="sm:hidden">RRHH</span>
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
