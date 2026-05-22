import { HeroSection, CompetitiveGapTable, ManifestoSection, ChallengeSolutionTable, SignupForm } from "@/features/salesbook";

export function SignupPage() {
  return (
    <div className="signup-page">
      <HeroSection />
      <CompetitiveGapTable />
      <ManifestoSection />
      <ChallengeSolutionTable />
      <SignupForm />
    </div>
  );
}
