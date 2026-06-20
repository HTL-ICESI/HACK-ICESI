import type { Metadata } from "next";
import { Cormorant } from "next/font/google";
import "./globals.css";

import { ThemeScript } from "@/components/theme/theme-script";

// Familia editorial secundaria del manual HG. La interfaz usa Gill Sans
// mediante fallbacks del sistema definidos en globals.css.
const editorial = Cormorant({
  subsets: ["latin"],
  variable: "--font-editorial",
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "WorkLab — riesgo laboral evitado, con su fuente · HG Hurtado Gandini",
  description:
    "WorkLab, la solución de compliance laboral vivo de HG Hurtado Gandini: Compliance Vivo y Disciplinario Blindado para derecho laboral colombiano.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={editorial.variable} suppressHydrationWarning>
      <body className="min-h-[100dvh] bg-background font-sans text-foreground antialiased">
        <ThemeScript />
        {children}
      </body>
    </html>
  );
}
