import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  /** El valor grande (cifra). */
  children: React.ReactNode;
  /** Badge de estado, normalmente "✓ calculado". */
  badge?: React.ReactNode;
  /** Nota/pie (porcentaje, fuente, motor de origen). */
  note?: React.ReactNode;
  /** Eleva con bezel (money shot); por defecto hairline. */
  featured?: boolean;
  className?: string;
}

export function MetricCard({
  label,
  children,
  badge,
  note,
  featured,
  className,
}: MetricCardProps) {
  return (
    <Card
      className={cn(
        "border-n300/60",
        featured ? "shadow-bezel" : "shadow-hairline",
        className,
      )}
    >
      <CardContent className="flex h-full flex-col p-6">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm text-muted-foreground">{label}</span>
          {badge}
        </div>
        <div className="mt-3 flex-1">{children}</div>
        {note && <div className="mt-3 text-sm text-muted-foreground">{note}</div>}
      </CardContent>
    </Card>
  );
}
