import type { Metadata } from "next";

import { Benefits } from "@/components/marketing/Benefits";
import { ClosingSection } from "@/components/marketing/ClosingSection";
import { Faq } from "@/components/marketing/Faq";
import { Hero } from "@/components/marketing/Hero";
import { MarketingFooter } from "@/components/marketing/MarketingFooter";
import { MarketingNav } from "@/components/marketing/MarketingNav";
import { MotorsSection } from "@/components/marketing/MotorsSection";
import { ProofSection } from "@/components/marketing/ProofSection";
import { VideoDemo } from "@/components/marketing/VideoDemo";

export const metadata: Metadata = {
  title: "Cerebro Laboral — Ve el riesgo antes de que cueste",
  description:
    "Compliance laboral vivo para firmas de derecho y sus clientes: detecta lo desactualizado, lo cuantifica en pesos y frena la nulidad antes de que ocurra.",
};

export default function LandingPage() {
  return (
    <>
      <MarketingNav />
      <main>
        <Hero />
        <VideoDemo />
        <MotorsSection />
        <ProofSection />
        <Benefits />
        <Faq />
        <ClosingSection />
      </main>
      <MarketingFooter />
    </>
  );
}
