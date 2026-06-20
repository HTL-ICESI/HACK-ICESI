import type { Metadata } from "next";
import { LoginPanel } from "@/components/auth/LoginPanel";

export const metadata: Metadata = {
  title: "Acceso — Cerebro Laboral HG",
  description: "Acceso exclusivo para abogados autorizados de Hurtado Gandini & Asociados.",
};

export default function LoginPage() {
  return <LoginPanel />;
}
