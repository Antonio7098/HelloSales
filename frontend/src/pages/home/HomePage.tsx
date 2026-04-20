import { DashboardHero } from "@/features/dashboard";
import { QualificationWorkflowPreview } from "@/workflows/qualification";

export function HomePage() {
  return (
    <>
      <DashboardHero />
      <QualificationWorkflowPreview />
    </>
  );
}
