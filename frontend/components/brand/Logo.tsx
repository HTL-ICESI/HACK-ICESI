import Image from "next/image";

import { cn } from "@/lib/utils";
import { WorkLabMark } from "./WorkLabMark";

type LogoTone = "dark" | "light";

interface IsotipoProps {
  className?: string;
  tone?: LogoTone;
  /** Envuelve el isotipo en un chip carbón (sello compacto sobre fondos claros). */
  badge?: boolean;
}

/** Isotipo WorkLab compacto. WorkLab es una solución de HG Hurtado Gandini. */
export function Isotipo({ className, tone = "dark", badge = false }: IsotipoProps) {
  if (!badge) {
    return (
      <WorkLabMark
        tone={tone}
        title="WorkLab"
        className={cn("size-8 shrink-0", className)}
      />
    );
  }
  return (
    <span
      className={cn(
        "inline-flex aspect-square shrink-0 items-center justify-center rounded-md bg-[#353535] p-1.5",
        className,
      )}
    >
      <WorkLabMark tone="light" title="WorkLab" className="size-full" />
    </span>
  );
}

/** Sello de origen HG — la firma que respalda y da nombre a WorkLab. */
export function HgSeal({
  tone = "dark",
  className,
}: {
  tone?: LogoTone;
  className?: string;
}) {
  const onDark = tone === "light";
  return (
    <span className={cn("flex items-center gap-2", className)}>
      <span
        aria-hidden="true"
        className={cn(
          "h-7 w-px shrink-0",
          onDark ? "bg-white/20" : "bg-[#D8D0CC] dark:bg-white/15",
        )}
      />
      <span
        className={cn(
          "inline-flex shrink-0 items-center overflow-hidden rounded-sm",
          onDark ? "bg-transparent" : "bg-[#353535] px-2 py-1.5",
        )}
      >
        <Image
          src="/brand/hg-horizontal-white.png"
          alt="HG Hurtado Gandini"
          width={1740}
          height={417}
          sizes="96px"
          className="h-5 w-auto object-contain"
        />
      </span>
    </span>
  );
}

// Lockup oficial (wordmark + isotipo + bajada «Laboratorio de Derecho Laboral»).
// PNG hand-painted con alpha; dimensiones intrínsecas reales por variante.
// El asset oscuro lleva sufijo `-v2`: versionar la URL al regenerar fuerza al
// navegador (y al optimizador de Next) a re-pedir la imagen en vez de servir la
// caché vieja, que mostraba una doble «K». Next no admite `?query` en imágenes
// locales sin configurar `images.localPatterns`, por eso versionamos el nombre.
const LOCKUP = {
  // ink oscuro → para fondos claros.
  onLight: { src: "/brand/worklab/lockup_light.png", w: 1980, h: 675 },
  // ink claro → para fondos oscuros (regenerado desde el lockup claro: una sola K).
  onDark: { src: "/brand/worklab/lockup_dark-v2.png", w: 1980, h: 675 },
} as const;

type LockupVariant = keyof typeof LOCKUP;

function LockupImage({
  variant,
  className,
}: {
  variant: LockupVariant;
  className?: string;
}) {
  const lockup = LOCKUP[variant];
  return (
    <Image
      src={lockup.src}
      alt="WorkLab, Laboratorio de Derecho Laboral"
      width={lockup.w}
      height={lockup.h}
      sizes="200px"
      className={cn("h-9 w-auto object-contain", className)}
    />
  );
}

interface LogoProps {
  className?: string;
  /** Sobrescribe el tamaño del lockup (alto). Por defecto `h-9 w-auto`. */
  imgClassName?: string;
  /** Sub-línea de origen: «una solución de HG Hurtado Gandini». */
  endorsement?: boolean;
  /** Añade el sello HG (logo horizontal) como respaldo de origen. */
  hgSeal?: boolean;
  /**
   * `dark` = sigue el tema de la página (ink oscuro en claro, claro en oscuro);
   * `light` = superficie permanentemente oscura (siempre ink claro).
   */
  tone?: LogoTone;
}

export function Logo({
  className,
  imgClassName,
  endorsement = false,
  hgSeal = false,
  tone = "dark",
}: LogoProps) {
  const onDark = tone === "light";

  return (
    <div className={cn("flex min-w-0 items-center gap-3", className)}>
      <div className="flex min-w-0 flex-col gap-1.5">
        {onDark ? (
          // Superficie fija oscura (sidebar carbón, panel de login): ink claro.
          <LockupImage variant="onDark" className={cn("block", imgClassName)} />
        ) : (
          // Sigue el tema: ink oscuro en claro, ink claro en modo oscuro.
          <>
            <LockupImage
              variant="onLight"
              className={cn("block dark:hidden", imgClassName)}
            />
            <LockupImage
              variant="onDark"
              className={cn("hidden dark:block", imgClassName)}
            />
          </>
        )}
        {endorsement && (
          <span
            className={cn(
              "truncate font-mono text-[10px] uppercase leading-none tracking-[0.12em]",
              onDark ? "text-lienzo/60" : "text-toga-300",
            )}
          >
            una solución de HG Hurtado Gandini
          </span>
        )}
      </div>

      {hgSeal && <HgSeal tone={tone} />}
    </div>
  );
}
