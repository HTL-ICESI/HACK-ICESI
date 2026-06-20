"use client";

import { Building2 } from "lucide-react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { usePersona } from "./persona-context";

/**
 * Selector de empresa cliente (F1). El bufete opera sobre varias empresas; el
 * dashboard y los flujos se recalculan para la empresa elegida.
 */
export function CompanySelector() {
  const { company, companies, setCompanyId } = usePersona();
  return (
    <Select value={company.id} onValueChange={setCompanyId}>
      <SelectTrigger className="w-[200px] md:w-[230px]">
        <div className="flex min-w-0 items-center gap-2">
          <Building2 className="size-4 shrink-0 text-muted-foreground" />
          <SelectValue placeholder="Empresa cliente" />
        </div>
      </SelectTrigger>
      <SelectContent>
        {companies.map((c) => (
          <SelectItem key={c.id} value={c.id}>
            {c.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
