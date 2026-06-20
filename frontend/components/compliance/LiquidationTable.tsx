"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";

import { Money } from "@/components/thesis/Money";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { downloadLiquidationExcel } from "@/lib/liquidation-excel";
import type { LiquidationRequest, LiquidationResponse } from "@/lib/types";

type PrestacionKey =
  | "cesantias"
  | "intereses_cesantias"
  | "prima"
  | "vacaciones";

// Prestaciones que suman el subtotal "TOTAL LIQUIDACIÓN" (total_prestaciones).
const PRESTACIONES: { key: PrestacionKey; label: string }[] = [
  { key: "cesantias", label: "Cesantías" },
  { key: "intereses_cesantias", label: "Intereses de cesantías" },
  { key: "prima", label: "Prima de servicios" },
  { key: "vacaciones", label: "Vacaciones" },
];

export function LiquidationTable({
  data,
  request,
}: {
  data: LiquidationResponse;
  /** Request usado para calcular — necesario para exportar el Excel HG. Si falta
   * (p.ej. flujo viejo), se intenta con el que adjunta el batch en `data.request`. */
  request?: LiquidationRequest;
}) {
  const i = data.items;
  const exportReq = request ?? data.request;
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(false);

  async function handleExport() {
    if (!exportReq) return;
    setExporting(true);
    setError(false);
    try {
      await downloadLiquidationExcel(exportReq);
    } catch {
      setError(true);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-n300/60 bg-card shadow-hairline">
      <div className="flex items-center justify-between border-b border-n300/50 px-4 py-2.5">
        <span className="text-[13px] font-medium text-muted-foreground">
          {error ? (
            <span className="text-risk-fg">No se pudo generar el Excel.</span>
          ) : (
            "Liquidación de prestaciones"
          )}
        </span>
        {exportReq && (
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="inline-flex items-center gap-1.5 rounded-md border border-acento/30 bg-acento/5 px-2.5 py-1.5 text-xs font-medium text-acento transition-colors hover:bg-acento/10 disabled:opacity-60"
          >
            {exporting ? (
              <Loader2 className="size-3.5 animate-spin" aria-hidden />
            ) : (
              <Download className="size-3.5" aria-hidden />
            )}
            Descargar Excel
          </button>
        )}
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Concepto</TableHead>
            <TableHead className="text-right">Valor</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {PRESTACIONES.map((row) => (
            <TableRow key={row.key}>
              <TableCell className="text-toga">{row.label}</TableCell>
              <TableCell className="text-right">
                <Money value={i[row.key]} />
              </TableCell>
            </TableRow>
          ))}

          {/* Subtotal de prestaciones = "TOTAL LIQUIDACIÓN" en el formato HG */}
          <TableRow className="bg-n100/60 hover:bg-n100/60">
            <TableCell className="font-semibold text-toga">
              Total liquidación{" "}
              <span className="font-normal text-muted-foreground">
                (prestaciones)
              </span>
            </TableCell>
            <TableCell className="text-right">
              <Money value={i.total_prestaciones} className="font-semibold" />
            </TableCell>
          </TableRow>

          {/* Indemnización: línea aparte (0 si renuncia / justa causa) */}
          <TableRow>
            <TableCell className="text-toga">
              Indemnización{" "}
              {i.indemnizacion === 0 && (
                <span className="text-xs text-muted-foreground">
                  · no aplica
                </span>
              )}
            </TableCell>
            <TableCell className="text-right">
              <Money value={i.indemnizacion} />
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>

      {/* Total general = exposición completa. Barra "money" (momento de credibilidad). */}
      <div className="flex items-center gap-3 border-t border-n300/50 bg-carbon px-4 py-3.5">
        <span className="flex-1 text-[13px] font-medium text-lienzo/70">
          Total a reconocer
        </span>
        <span className="inline-flex items-center gap-1 rounded bg-[#F4F1EF] px-2 py-0.5 font-mono text-[11px] font-medium text-[#2E7D32]">
          ✓ calculado
        </span>
        <Money
          value={i.total}
          className="font-display text-[1.375rem] font-medium text-lienzo tnum"
        />
      </div>
    </div>
  );
}
