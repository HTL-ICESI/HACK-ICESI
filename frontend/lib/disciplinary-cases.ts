"use client";

import type { DiligenceMeta } from "@/components/disciplinary/DiligenceForm";

/** Un caso disciplinario abierto sobre un trabajador (estado de sesión de la demo). */
export interface DiscCase extends DiligenceMeta {
  id: string;
  telefono: string;
  createdAt: string;
  status: "abierto" | "cerrado";
}

const CASES_KEY = (companyId: string) => `disc-cases:${companyId}`;
const PHONES_KEY = (companyId: string) => `worker-phones:${companyId}`;

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

// ── Casos ────────────────────────────────────────────────────────────────────

export function loadCases(companyId: string): DiscCase[] {
  return read<DiscCase[]>(CASES_KEY(companyId), []);
}

export function addCase(
  companyId: string,
  meta: DiligenceMeta,
  telefono: string,
): DiscCase {
  const c: DiscCase = {
    ...meta,
    id: `case-${Date.now().toString(36)}`,
    telefono,
    createdAt: new Date().toISOString(),
    status: "abierto",
  };
  const next = [c, ...loadCases(companyId)];
  localStorage.setItem(CASES_KEY(companyId), JSON.stringify(next));
  return c;
}

export function removeCase(companyId: string, id: string): void {
  const next = loadCases(companyId).filter((c) => c.id !== id);
  localStorage.setItem(CASES_KEY(companyId), JSON.stringify(next));
}

export function setCasePhone(companyId: string, id: string, telefono: string): void {
  const next = loadCases(companyId).map((c) =>
    c.id === id ? { ...c, telefono } : c,
  );
  localStorage.setItem(CASES_KEY(companyId), JSON.stringify(next));
}

// ── Directorio de contacto del trabajador (su celular viene de la ficha) ──────

/** Genera un celular colombiano estable a partir de una clave (doc_id/nombre).
 * Determinista: el mismo trabajador siempre muestra el mismo número registrado. */
function seededPhone(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  const nine = String(h % 1_000_000_000).padStart(9, "0");
  return `+57 3${nine.slice(0, 2)} ${nine.slice(2, 5)} ${nine.slice(5, 9)}`;
}

/** Celular registrado del trabajador: override guardado, o el sembrado de su ficha. */
export function workerPhone(companyId: string, key: string): string {
  const overrides = read<Record<string, string>>(PHONES_KEY(companyId), {});
  return overrides[key] ?? seededPhone(key || "trabajador");
}

export function setWorkerPhone(companyId: string, key: string, phone: string): void {
  const overrides = read<Record<string, string>>(PHONES_KEY(companyId), {});
  overrides[key] = phone;
  localStorage.setItem(PHONES_KEY(companyId), JSON.stringify(overrides));
}
