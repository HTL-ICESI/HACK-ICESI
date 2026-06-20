"use client";

import { Search } from "lucide-react";

import { cn } from "@/lib/utils";
import type { RiskLevel } from "./risk";

export interface BatchFilterState {
  query: string;
  risk: RiskLevel | "todos";
  gap: string | "todos";
}

const RISKS: { value: RiskLevel | "todos"; label: string }[] = [
  { value: "todos", label: "Todos" },
  { value: "alto", label: "Alto" },
  { value: "medio", label: "Medio" },
  { value: "bajo", label: "Bajo" },
];

const GAPS = ["todos", "g1", "g2", "g3", "g4", "g5"];

export function BatchFilters({
  value,
  onChange,
}: {
  value: BatchFilterState;
  onChange: (v: BatchFilterState) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative min-w-[14rem] flex-1">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <input
          value={value.query}
          onChange={(e) => onChange({ ...value, query: e.target.value })}
          placeholder="Buscar empleado…"
          className="w-full rounded-md border border-n300 bg-card py-2 pl-9 pr-3 text-sm text-toga outline-none focus:border-acento"
        />
      </div>

      <div className="flex items-center gap-1">
        {RISKS.map((r) => (
          <button
            key={r.value}
            onClick={() => onChange({ ...value, risk: r.value })}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
              value.risk === r.value
                ? "bg-acento text-white"
                : "bg-card text-muted-foreground hover:text-toga",
            )}
          >
            {r.label}
          </button>
        ))}
      </div>

      <select
        value={value.gap}
        onChange={(e) => onChange({ ...value, gap: e.target.value })}
        className="rounded-md border border-n300 bg-card px-3 py-2 text-xs text-toga outline-none focus:border-acento"
      >
        {GAPS.map((g) => (
          <option key={g} value={g}>
            {g === "todos" ? "Todos los gaps" : g.toUpperCase()}
          </option>
        ))}
      </select>
    </div>
  );
}
