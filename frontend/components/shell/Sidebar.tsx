"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Layers,
  LogOut,
  ShieldAlert,
  Users,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Logo } from "@/components/brand/Logo";
import { logout } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { PersonaSwitch } from "./PersonaSwitch";
import { type Persona, usePersona } from "./persona-context";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  personas: Persona[];
  group: string;
}

// El nav se adapta a la persona: Abogado ve los motores; RRHH ve lo accionable.
const NAV: NavItem[] = [
  {
    href: "/dashboard",
    label: "Inicio",
    icon: LayoutDashboard,
    personas: ["abogado", "rrhh"],
    group: "General",
  },
  {
    href: "/batch",
    label: "Compliance",
    icon: Layers,
    personas: ["abogado"],
    group: "Motores",
  },
  {
    href: "/disciplinario",
    label: "Disciplinario Blindado",
    icon: ShieldAlert,
    personas: ["abogado"],
    group: "Motores",
  },
  {
    href: "/equipo",
    label: "Alertas y equipo",
    icon: Users,
    personas: ["rrhh"],
    group: "General",
  },
];

// Fallback si aún no cargó la sesión (cliente). El usuario real viene de la sesión.
const FALLBACK_USER: Record<Persona, { initials: string; name: string; sub: string }> =
  {
    abogado: { initials: "JP", name: "Dra. Juliana Pardo", sub: "Hurtado Gandini" },
    rrhh: { initials: "AM", name: "Andrés Marín", sub: "Jefe de Personal" },
  };

interface SidebarProps {
  mobileOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { persona, user: sessionUser } = usePersona();
  const user = sessionUser
    ? { initials: sessionUser.initials, name: sessionUser.name, sub: sessionUser.title }
    : FALLBACK_USER[persona];

  function handleLogout() {
    logout();
    router.push("/login");
  }

  const items = NAV.filter((item) => item.personas.includes(persona));
  const groups = items.reduce<Record<string, NavItem[]>>((acc, item) => {
    (acc[item.group] ??= []).push(item);
    return acc;
  }, {});

  return (
    <>
      {/* Backdrop (solo mobile) */}
      {mobileOpen && (
        <button
          aria-label="Cerrar menú"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-carbon/50 backdrop-blur-sm md:hidden"
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-carbon text-lienzo transition-transform duration-300 ease-fluid md:static md:z-auto md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        )}
      >
        {/* Brand */}
        <div className="flex h-16 items-center justify-between px-5">
          <Logo tone="light" />
          <button
            aria-label="Cerrar menú"
            onClick={onClose}
            className="rounded-md p-1 text-lienzo/70 hover:bg-white/10 md:hidden"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Switch de persona (solo mobile; en desktop vive en el topbar) */}
        <div className="px-3 pb-2 md:hidden">
          <PersonaSwitch />
        </div>

        {/* Nav */}
        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
          {Object.entries(groups).map(([group, groupItems]) => (
            <div key={group} className="space-y-1">
              <p className="px-3 pb-1 font-mono text-[10px] uppercase tracking-[0.18em] text-lienzo/40">
                {group}
              </p>
              {groupItems.map((item) => {
                const active =
                  pathname === item.href ||
                  pathname.startsWith(`${item.href}/`);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    className={cn(
                      "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "bg-white/10 text-lienzo"
                        : "text-lienzo/65 hover:bg-white/5 hover:text-lienzo",
                    )}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-acento" />
                    )}
                    <Icon className="size-4 shrink-0" aria-hidden="true" />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Usuario + cerrar sesión */}
        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-3 rounded-md px-2 py-2">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-white/10 font-mono text-xs font-medium text-lienzo">
              {user.initials}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-lienzo">
                {user.name}
              </p>
              <p className="truncate text-xs text-lienzo/50">{user.sub}</p>
            </div>
            <button
              onClick={handleLogout}
              aria-label="Cerrar sesión"
              title="Cerrar sesión"
              className="shrink-0 rounded-md p-1.5 text-lienzo/60 transition-colors hover:bg-white/10 hover:text-lienzo"
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
