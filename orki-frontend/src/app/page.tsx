import { CtaSection } from "@/widgets/landing/cta-section";
import { FeaturesSection } from "@/widgets/landing/features-section";
import { HeroSection } from "@/widgets/landing/hero-section";
import { LandingNav } from "@/widgets/landing/landing-nav";
import { ResultsSection } from "@/widgets/landing/results-section";
import { ShowcaseSection } from "@/widgets/landing/showcase-section";

export default function Home() {
  return (
    <>
      <LandingNav />
      <HeroSection />
      <FeaturesSection />
      <ShowcaseSection />
      <ResultsSection />
      <CtaSection />
    </>
  );
}
