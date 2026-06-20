"use client";

/**
 * Sesión y roles (mock de auth para el MVP; en producción sería JWT contra el backend).
 *
 * El ROL determina la VISTA y los permisos:
 *  - `abogado` → Firma (Hurtado Gandini): exposición consolidada, compliance en lote,
 *    disciplinario blindado. Es quien FIRMA documentos y conduce las diligencias.
 *  - `rrhh`    → Empresa cliente: vista accionable (alertas y equipo), sin los motores
 *    jurídicos. No firma; ejecuta tareas operativas.
 *
 * El nombre del usuario se usa para: saludo (RRHH), firma de documentos (abogado) y el
 * mensaje de WhatsApp al trabajador (para que sepa qué abogado lleva su proceso).
 */
export type Role = "abogado" | "rrhh";

export interface SessionUser {
  email: string;
  name: string; // nombre completo, p.ej. "Dra. Juliana Pardo"
  shortName: string; // para el saludo, p.ej. "Juliana"
  role: Role;
  title: string; // cargo
  org: string; // firma o empresa
  initials: string;
}

// Directorio demo (en prod: tabla de usuarios con hash + roles).
const DIRECTORY: Record<string, SessionUser> = {
  "abogado@hurtadogandini.co": {
    email: "abogado@hurtadogandini.co",
    name: "Dra. Juliana Pardo",
    shortName: "Juliana",
    role: "abogado",
    title: "Abogada laboral senior",
    org: "Hurtado Gandini & Asociados",
    initials: "JP",
  },
  "demo@hurtadogandini.co": {
    email: "demo@hurtadogandini.co",
    name: "Dra. Juliana Pardo",
    shortName: "Juliana",
    role: "abogado",
    title: "Abogada laboral senior",
    org: "Hurtado Gandini & Asociados",
    initials: "JP",
  },
  "jurado@icesi.edu.co": {
    email: "jurado@icesi.edu.co",
    name: "Dr. Jurado ICESI",
    shortName: "Jurado",
    role: "abogado",
    title: "Abogado evaluador",
    org: "Hurtado Gandini & Asociados",
    initials: "JI",
  },
  "rrhh@empresacliente.co": {
    email: "rrhh@empresacliente.co",
    name: "Andrés Marín",
    shortName: "Andrés",
    role: "rrhh",
    title: "Jefe de Personal",
    org: "Empresa Cliente SAS",
    initials: "AM",
  },
};

const KEY = "hg_session";

/** Valida el correo contra el directorio y abre sesión. null si no existe. */
export function login(email: string): SessionUser | null {
  const u = DIRECTORY[email.trim().toLowerCase()];
  if (!u) return null;
  try {
    localStorage.setItem(KEY, JSON.stringify(u));
  } catch {
    /* noop */
  }
  return u;
}

export function getSession(): SessionUser | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as SessionUser) : null;
  } catch {
    return null;
  }
}

export function logout(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* noop */
  }
}

export function knownEmails(): string[] {
  return Object.keys(DIRECTORY);
}
