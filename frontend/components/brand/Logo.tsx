import Image from "next/image";

import { cn } from "@/lib/utils";

type LogoTone = "dark" | "light";

interface IsotipoProps {
  className?: string;
  tone?: LogoTone;
}

/**
 * Firma compacta oficial HG. La versión blanca siempre vive sobre una
 * superficie aprobada: carbón en fondos claros o directamente sobre oscuro.
 */
export function Isotipo({ className, tone = "dark" }: IsotipoProps) {
  return (
    <span
      className={cn(
        "relative inline-flex aspect-square shrink-0 overflow-hidden rounded-sm p-1",
        tone === "dark" ? "bg-[#353535]" : "bg-transparent",
        className,
      )}
    >
      <Image
        src="/brand/hg-vertical-white.png"
        alt=""
        fill
        sizes="32px"
        className="object-contain"
      />
    </span>
  );
}

interface LogoProps {
  className?: string;
  isotipoClassName?: string;
  /** Muestra el nombre del producto junto a la firma corporativa. */
  wordmark?: boolean;
  /** `dark` sobre fondo claro; `light` sobre una superficie oscura. */
  tone?: LogoTone;
}

export function Logo({
  className,
  isotipoClassName,
  wordmark = true,
  tone = "dark",
}: LogoProps) {
  const onDark = tone === "light";

  return (
    <div className={cn("flex min-w-0 items-center gap-2.5", className)}>
      <span
        className={cn(
          "inline-flex shrink-0 items-center overflow-hidden rounded-sm",
          onDark ? "bg-transparent" : "bg-[#353535] px-2.5 py-1.5",
        )}
      >
        <Image
          src="/brand/hg-horizontal-white.png"
          alt="HG Hurtado Gandini"
          width={1740}
          height={417}
          sizes="132px"
          priority
          className={cn(
            "w-auto object-contain",
            onDark ? "h-6" : "h-7",
            isotipoClassName,
          )}
        />
      </span>

      {wordmark && (
        <>
          <span
            aria-hidden="true"
            className={cn(
              "h-7 w-px shrink-0",
              onDark ? "bg-white/25" : "bg-[#D8D0CC]",
              "hidden sm:block",
            )}
          />
          <span
            className={cn(
              "truncate font-sans font-medium leading-none tracking-[-0.01em]",
              onDark ? "text-[13px]" : "text-[15px]",
              "hidden sm:block",
              onDark ? "text-[#FBFAF9]" : "text-[#353535]",
            )}
          >
            Cerebro Laboral
          </span>
        </>
      )}
    </div>
  );
}
