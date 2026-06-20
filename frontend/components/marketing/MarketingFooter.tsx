import { Logo } from "@/components/brand/Logo";

export function MarketingFooter() {
  return (
    <footer className="border-t border-n300/60 bg-surface px-6 py-7">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center gap-4">
          <Logo hgSeal />
          <span className="text-[13px] text-toga-300">
            © 2026 · WorkLab · una solución de HG Hurtado Gandini
          </span>
          <nav
            className="ml-auto flex gap-5 text-[13px]"
            aria-label="Pie de página"
          >
            <a href="#faq" className="text-toga-300 hover:text-toga">
              Privacidad
            </a>
            <a href="#faq" className="text-toga-300 hover:text-toga">
              Términos
            </a>
            <a href="/equipo" className="text-toga-300 hover:text-toga">
              Contacto
            </a>
          </nav>
        </div>

        {/* Disclaimer legal (se conserva: producto legaltech) */}
        <p className="mt-5 border-t border-n300/50 pt-4 text-xs leading-relaxed text-toga-300">
          La plataforma asiste al profesional del derecho; no constituye asesoría
          jurídica ni sustituye el criterio del abogado a cargo.
        </p>
      </div>
    </footer>
  );
}
