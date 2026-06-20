import type { Config } from "tailwindcss";

/**
 * Sistema de diseño WorkLab — una solución de HG Hurtado Gandini (Manual HG v1.2).
 * - Tokens semánticos de shadcn como tripletas HSL (para que `bg-primary/90` etc. funcionen en v3).
 * - Tokens de marca y semáforo de estado en hex/rgba (DESIGN.md §2), usados directamente.
 * Los nombres históricos `toga` y `acento` se conservan como aliases para no
 * modificar la estructura de componentes; sus valores ya corresponden a HG.
 */
const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1200px" },
    },
    extend: {
      colors: {
        // ── shadcn semantic (HSL en globals.css) ──
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        // shadcn `accent` = fondo rojo HG suave de hover.
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },

        // ── Marca HG v1.1 ── (canales RGB en globals.css :root / .dark → theming)
        // `carbon` y `lienzo` son FIJOS (superficies oscuras de marca + texto claro
        // sobre ellas). El resto invierte en modo oscuro vía las variables .dark.
        carbon: {
          DEFAULT: "rgb(var(--carbon) / <alpha-value>)",
          700: "rgb(var(--carbon-700) / <alpha-value>)",
        },
        "hg-gray": "rgb(var(--hg-gray) / <alpha-value>)",
        "hg-red": {
          DEFAULT: "rgb(var(--hg-red) / <alpha-value>)",
          soft: "rgb(var(--hg-red-soft) / <alpha-value>)",
        },
        wine: {
          DEFAULT: "rgb(var(--wine) / <alpha-value>)",
          soft: "rgb(var(--wine-soft) / <alpha-value>)",
        },

        // Aliases compatibles con las clases existentes (mismos nombres de token).
        toga: {
          DEFAULT: "rgb(var(--toga) / <alpha-value>)",
          700: "rgb(var(--toga-700) / <alpha-value>)",
          300: "rgb(var(--toga-300) / <alpha-value>)",
        },
        acento: {
          DEFAULT: "rgb(var(--acento) / <alpha-value>)",
          soft: "rgb(var(--acento-soft) / <alpha-value>)",
        },
        accion: {
          DEFAULT: "rgb(var(--accion) / <alpha-value>)",
          soft: "rgb(var(--accion-soft) / <alpha-value>)",
        },
        lienzo: "rgb(var(--lienzo) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        n100: "rgb(var(--n100) / <alpha-value>)",
        n300: "rgb(var(--n300) / <alpha-value>)",
        body: "rgb(var(--body) / <alpha-value>)",

        // ── Semáforo de ESTADO (nunca decorativo). soft = relleno, fg = texto ──
        ok: {
          DEFAULT: "rgb(var(--ok) / <alpha-value>)",
          fg: "rgb(var(--ok-fg) / <alpha-value>)",
          soft: "rgb(var(--ok) / 0.14)",
        },
        warn: {
          DEFAULT: "rgb(var(--warn) / <alpha-value>)",
          fg: "rgb(var(--warn-fg) / <alpha-value>)",
          soft: "rgb(var(--warn) / 0.16)",
        },
        risk: {
          DEFAULT: "rgb(var(--risk) / <alpha-value>)",
          fg: "rgb(var(--risk-fg) / <alpha-value>)",
          soft: "rgb(var(--risk) / 0.12)",
        },
        info: {
          DEFAULT: "rgb(var(--info) / <alpha-value>)",
          fg: "rgb(var(--info-fg) / <alpha-value>)",
          soft: "rgb(var(--info) / 0.16)",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: [
          "var(--font-sans)",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "Menlo", "monospace"],
        serif: ["var(--font-editorial)", "Cormorant", "Georgia", "serif"],
      },
      fontSize: {
        // Money shot y display en Gill Sans, según el manual HG v1.1.
        money: ["3.5rem", { lineHeight: "1.05", fontWeight: "500" }], // 56px
        "money-sm": ["2rem", { lineHeight: "1.1", fontWeight: "500" }], // 32px (mobile)
        display: ["2.5rem", { lineHeight: "1.1", fontWeight: "500" }], // 40px
      },
      transitionTimingFunction: {
        // Paneles/drawers en movimiento (curva de drawer iOS).
        fluid: "cubic-bezier(0.32, 0.72, 0, 1)",
        // Entradas / ease-out fuerte (más "punch" que el ease-out nativo).
        snappy: "cubic-bezier(0.23, 1, 0.32, 1)",
      },
      boxShadow: {
        hairline: "0 0 0 1px rgba(53,53,53,0.07)",
        bezel:
          "0 0 0 1px rgba(53,53,53,0.07), inset 0 1px 0 rgba(255,255,255,0.85), 0 2px 4px rgba(53,53,53,0.04), 0 14px 36px rgba(53,53,53,0.07)",
        "bezel-hover":
          "0 0 0 1px rgba(128,24,23,0.30), inset 0 1px 0 rgba(255,255,255,0.9), 0 4px 8px rgba(53,53,53,0.06), 0 22px 52px rgba(53,53,53,0.12)",
        "glow-red": "0 0 0 1px rgba(128,24,23,0.22), 0 10px 30px -6px rgba(128,24,23,0.35)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        // Barras que crecen al entrar (composición, % cláusulas, vacaciones). Requiere origin-left.
        "grow-x": {
          from: { transform: "scaleX(0)" },
          to: { transform: "scaleX(1)" },
        },
        // Latido sutil del banner de nulidad (el momento wow). Rojo, muy contenido.
        "soft-pulse": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(128,24,23,0)" },
          "50%": { boxShadow: "0 0 0 4px rgba(128,24,23,0.12)" },
        },
        // Deriva muy lenta del glow del átomo (fondo de la landing).
        drift: {
          "0%, 100%": { transform: "translate3d(0,0,0) scale(1)", opacity: "0.9" },
          "50%": { transform: "translate3d(2%,-2%,0) scale(1.06)", opacity: "1" },
        },
        // Respiración sutil del halo (escala + opacidad).
        breathe: {
          "0%, 100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "0.8", transform: "scale(1.04)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "grow-x": "grow-x 0.7s cubic-bezier(0.23,1,0.32,1) both",
        "soft-pulse": "soft-pulse 2.4s ease-in-out infinite",
        drift: "drift 26s ease-in-out infinite",
        breathe: "breathe 9s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
