"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getSession, type SessionUser } from "@/lib/auth";

/**
 * Estado del shell (F1): la persona/vista activa, el usuario en sesión y la empresa.
 * La VISTA la determina el ROL del usuario (abogado · Firma / rrhh · Empresa). El
 * `setPersona` queda como override de demostración (para revisar ambas vistas sin
 * volver a iniciar sesión); en producción la vista está fija por rol.
 * - Abogado · Firma: experto, denso, con citas. Firma documentos.
 * - RRHH · Empresa cliente: operador, accionable, baja densidad.
 */
export type Persona = "abogado" | "rrhh";

export interface Company {
  id: string;
  name: string;
}

// Mock: empresas cliente del bufete (auth y multi-tenant son mock en el MVP).
const COMPANIES: Company[] = [
  { id: "empresa-001", name: "Empresa Cliente SAS" },
  { id: "empresa-002", name: "Logística Andina SAS" },
  { id: "empresa-003", name: "Comercial del Valle Ltda" },
];

interface PersonaContextValue {
  persona: Persona;
  setPersona: (p: Persona) => void;
  user: SessionUser | null;
  company: Company;
  setCompanyId: (id: string) => void;
  companies: Company[];
}

const PersonaContext = createContext<PersonaContextValue | null>(null);

export function PersonaProvider({ children }: { children: React.ReactNode }) {
  const [persona, setPersona] = useState<Persona>("abogado");
  const [user, setUser] = useState<SessionUser | null>(null);
  const [companyId, setCompanyId] = useState<string>(COMPANIES[0].id);

  // La vista la fija el rol del usuario en sesión (cliente; localStorage).
  useEffect(() => {
    const s = getSession();
    if (s) {
      setUser(s);
      setPersona(s.role);
    }
  }, []);

  const value = useMemo<PersonaContextValue>(() => {
    const company =
      COMPANIES.find((c) => c.id === companyId) ?? COMPANIES[0];
    return { persona, setPersona, user, company, setCompanyId, companies: COMPANIES };
  }, [persona, user, companyId]);

  return (
    <PersonaContext.Provider value={value}>{children}</PersonaContext.Provider>
  );
}

export function usePersona(): PersonaContextValue {
  const ctx = useContext(PersonaContext);
  if (!ctx) {
    throw new Error("usePersona debe usarse dentro de <PersonaProvider>");
  }
  return ctx;
}
