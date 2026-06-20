"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Loader2, Lock, Shield, ShieldCheck, Star } from "lucide-react";

import { Isotipo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { login as openSession } from "@/lib/auth";

// Credenciales demo — en producción esto sería JWT contra el backend.
// El correo determina el ROL (abogado · Firma / rrhh · Empresa). Acepta
// cualquier correo con contraseña Demo2026! para flexibilidad de demo.
const DEMO_PASSWORD = "Demo2026!";
const DEMO_CREDENTIALS = [
  { email: "abogado@hurtadogandini.co", password: DEMO_PASSWORD },
  { email: "demo@hurtadogandini.co",    password: DEMO_PASSWORD },
  { email: "jurado@icesi.edu.co",       password: DEMO_PASSWORD },
  { email: "rrhh@empresacliente.co",    password: DEMO_PASSWORD },
  { email: "demo@worklab.co",           password: DEMO_PASSWORD },
  { email: "admin@worklab.co",          password: DEMO_PASSWORD },
];

const SECURITY_FEATURES = [
  "Cifrado TLS 1.3 en tránsito",
  "Acceso por rol — solo abogados autorizados",
  "Sesión con tiempo de expiración automático",
  "Trazabilidad completa de cada consulta",
];

export function LoginPanel() {
  const router = useRouter();
  const [email, setEmail]     = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    // Simular latencia de red real
    await new Promise((r) => setTimeout(r, 900));

    const emailNorm = email.trim().toLowerCase();
    // Modo demo: cualquier email válido + contraseña Demo2026! ingresa.
    // En producción reemplazar por llamada JWT al backend.
    const valid =
      password === DEMO_PASSWORD && emailNorm.includes("@") ||
      DEMO_CREDENTIALS.some(
        (c) => c.email === emailNorm && c.password === password,
      );

    if (!valid) {
      setLoading(false);
      setError(
        password !== DEMO_PASSWORD
          ? `Contraseña incorrecta. Use: Demo2026!`
          : "Credenciales incorrectas. Verifique su correo y contraseña.",
      );
      return;
    }

    // Abrir sesión con el usuario + rol del directorio (lo lee toda la app).
    openSession(email);
    router.push("/dashboard");
  }

  return (
    <div className="flex min-h-screen">
      {/* ── Panel izquierdo — Identidad y seguridad ── */}
      <div className="relative hidden flex-col justify-between bg-carbon p-10 lg:flex lg:w-[52%] xl:w-[55%]">
        {/* Glow de marca */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(70%_60%_at_80%_100%,rgba(59,67,201,0.35),transparent_65%)]"
        />

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <Isotipo className="size-9" tone="light" />
          <div>
            <p className="font-display text-[18px] font-semibold leading-none tracking-tight text-lienzo">
              Cerebro <span className="text-[#818cf8]">Laboral</span>
            </p>
            <p className="mt-0.5 font-mono text-[11px] uppercase tracking-widest text-lienzo/50">
              Hurtado Gandini & Asociados
            </p>
          </div>
        </div>

        {/* Cuerpo principal */}
        <div className="relative max-w-md space-y-8">
          <div>
            <span className="inline-flex rounded-full border border-lienzo/20 bg-lienzo/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] text-lienzo/70">
              Plataforma interna · Solo uso autorizado
            </span>
            <h1 className="mt-5 font-display text-[clamp(2rem,3.5vw,3rem)] font-medium leading-[1.05] tracking-tight text-lienzo">
              Los datos de sus clientes merecen el mismo rigor que su defensa.
            </h1>
            <p className="mt-4 text-[15px] leading-relaxed text-lienzo/65">
              Cerebro Laboral procesa contratos laborales sensibles bajo
              protocolos de seguridad de nivel empresarial. Solo personal
              autorizado tiene acceso.
            </p>
          </div>

          {/* Features de seguridad */}
          <ul className="space-y-3">
            {SECURITY_FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-3">
                <ShieldCheck className="size-4 shrink-0 text-[#818cf8]" />
                <span className="text-sm text-lienzo/75">{f}</span>
              </li>
            ))}
          </ul>

          {/* Badge de cumplimiento */}
          <div className="inline-flex items-center gap-2 rounded-xl border border-lienzo/15 bg-white/10 px-4 py-3">
            <Shield className="size-4 text-[#818cf8]" />
            <span className="text-sm text-lienzo/70">
              Datos tratados conforme a la{" "}
              <span className="font-medium text-lienzo/90">Ley 1581 de 2012</span>{" "}
              · Habeas Data Colombia
            </span>
          </div>
        </div>

        {/* Footer del panel */}
        <p className="relative font-mono text-[11px] text-lienzo/35">
          © 2026 Hurtado Gandini & Asociados SAS · Uso exclusivo interno
        </p>
      </div>

      {/* ── Panel derecho — Formulario ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        {/* Logo mobile */}
        <div className="mb-10 flex items-center gap-2 lg:hidden">
          <Isotipo className="size-7" tone="dark" />
          <span className="font-display text-[17px] font-semibold text-toga">
            Cerebro <span className="text-acento">Laboral</span>
          </span>
        </div>

        <div className="w-full max-w-sm">
          <div className="mb-8">
            <h2 className="font-display text-2xl font-semibold text-toga">
              Iniciar sesión
            </h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Acceso exclusivo para abogados autorizados.
            </p>
          </div>

          <form ref={formRef} onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="email" className="text-sm font-medium text-toga">Correo corporativo</label>
                <button
                  type="button"
                  title="Acceso demo instantáneo"
                  onClick={() => {
                    setEmail("abogado@hurtadogandini.co");
                    setPassword("Demo2026!");
                    setError(null);
                    // Auto-submit tras el siguiente tick (espera a que React actualice el estado)
                    setTimeout(() => formRef.current?.requestSubmit(), 50);
                  }}
                  className="flex items-center gap-1 rounded-full bg-acento px-2.5 py-0.5 text-[11px] font-medium text-white transition-colors hover:bg-acento/90"
                >
                  <Star className="size-3 fill-white" />
                  Acceso demo
                </button>
              </div>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="nombre@hurtadogandini.co"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium text-toga">Contraseña</label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPwd ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-toga"
                  tabIndex={-1}
                  aria-label={showPwd ? "Ocultar contraseña" : "Mostrar contraseña"}
                >
                  {showPwd ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </div>

            {error && (
              <p className="rounded-lg border border-risk/30 bg-risk-soft px-3 py-2.5 text-sm text-risk-fg">
                {error}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Verificando acceso…
                </>
              ) : (
                <>
                  <Lock className="size-4" />
                  Entrar al sistema
                </>
              )}
            </Button>
          </form>

          {/* Hint de credenciales demo */}
          <div className="mt-6 rounded-xl border border-n300/60 bg-n100/60 px-4 py-3">
            <p className="text-xs font-medium text-toga">Credenciales demo · por rol</p>
            <p className="mt-1.5 font-mono text-[11px] text-muted-foreground">
              Abogado (Firma): abogado@hurtadogandini.co
            </p>
            <p className="font-mono text-[11px] text-muted-foreground">
              RRHH (Empresa): rrhh@empresacliente.co
            </p>
            <p className="mt-1 font-mono text-[11px] text-muted-foreground">
              Contraseña: Demo2026!
            </p>
          </div>

          <div className="mt-8 flex items-center justify-between text-xs text-muted-foreground">
            <Link href="/" className="hover:text-toga">
              ← Volver al inicio
            </Link>
            <span className="flex items-center gap-1">
              <ShieldCheck className="size-3 text-ok" />
              Conexión segura
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
