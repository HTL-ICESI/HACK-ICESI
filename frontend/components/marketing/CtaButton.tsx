import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "onDark";

interface CtaButtonProps {
  href: string;
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}

const VARIANTS: Record<Variant, string> = {
  primary: "bg-toga text-lienzo hover:bg-toga-700 pl-5 pr-2",
  onDark: "bg-lienzo text-toga hover:bg-white pl-5 pr-2",
  secondary:
    "border border-n300 text-toga hover:border-toga/40 hover:bg-n100 px-5",
};

const ICON_CIRCLE: Record<Variant, string> = {
  primary: "bg-white/15",
  onDark: "bg-toga/10",
  secondary: "",
};

/**
 * CTA en pill con flecha anidada en su propio círculo (button-in-button) y
 * hover magnético. Sirve para anclas (#...) y rutas (/dashboard).
 */
export function CtaButton({
  href,
  children,
  variant = "primary",
  className,
}: CtaButtonProps) {
  const withIcon = variant !== "secondary";
  return (
    <Link
      href={href}
      className={cn(
        "group inline-flex items-center gap-2 rounded-full py-2 text-sm font-medium transition-[transform,background-color] duration-150 ease-out active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acento focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        VARIANTS[variant],
        className,
      )}
    >
      <span>{children}</span>
      {withIcon && (
        <span
          className={cn(
            "flex size-7 items-center justify-center rounded-full transition-transform duration-200 ease-out [@media(hover:hover)]:group-hover:translate-x-0.5 [@media(hover:hover)]:group-hover:-translate-y-px",
            ICON_CIRCLE[variant],
          )}
        >
          <ArrowRight className="size-3.5" aria-hidden="true" />
        </span>
      )}
    </Link>
  );
}
