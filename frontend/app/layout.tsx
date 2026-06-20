import type { Metadata } from "next";
import { Cormorant } from "next/font/google";
import "./globals.css";

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
  title: "Cerebro Laboral — riesgo laboral evitado, con su fuente",
  description:
    "Compliance Vivo y Disciplinario Blindado para derecho laboral colombiano.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={editorial.variable}>
      <body className="min-h-[100dvh] bg-background font-sans text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
