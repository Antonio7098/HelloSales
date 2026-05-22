import { Button } from "@/design-system";
import type { OnboardingProgress, Registry } from "@/entities/salesbook/types";
import { IconArrow, IconArrowLeft } from "@/shared/icons/NavIcons";
import { groupBySection, pctNumber } from "../model/onboarding";

export function FinalRecap({
  registry,
  responses,
  progress,
  onBackToOnboarding,
  onDone,
}: {
  registry: Registry;
  responses: Record<string, string>;
  progress: OnboardingProgress | null;
  onBackToOnboarding: () => void;
  onDone: () => void;
}) {
  const groups = groupBySection(registry);
  const registryKeys = Object.keys(registry);
  const totalAnswered = registryKeys.filter((key) => (responses[key] ?? "").trim() !== "").length;
  const totalQuestions = registryKeys.length;

  return (
    <div className="onboarding-final">
      <div className="onboarding-final-eyebrow">Hello Sales · your business IQ</div>
      <h1 className="onboarding-final-title">Here's what your sales agents now know.</h1>
      <p className="onboarding-final-sub">
        {totalAnswered} of {totalQuestions} questions answered
        {progress ? ` · ${pctNumber(progress.total_completion_pct).toFixed(0)}% complete` : ""}.
        This is the foundation every rep, every call, and every agent will draw from.
      </p>

      <div className="onboarding-final-body">
        {groups.map((group) => {
          const answered = group.questions.filter((question) => (responses[question.key] ?? "").trim() !== "");
          if (answered.length === 0) return null;
          return (
            <section key={`${group.phase}-${group.section}`} className="onboarding-final-section">
              <header className="onboarding-final-section-head">
                <span className="onboarding-final-section-phase">Phase {group.phase}</span>
                <h2 className="onboarding-final-section-title">{group.section}</h2>
                <span className="onboarding-final-section-count">
                  {answered.length}/{group.questions.length}
                </span>
              </header>
              <dl className="onboarding-final-list">
                {answered.map((question) => (
                  <div key={question.key} className="onboarding-final-item">
                    <dt>{question.question}</dt>
                    <dd>{responses[question.key]}</dd>
                  </div>
                ))}
              </dl>
            </section>
          );
        })}
      </div>

      <footer className="onboarding-footer">
        <Button variant="ghost" onClick={onBackToOnboarding} leading={<IconArrowLeft />}>
          Back to onboarding
        </Button>
        <Button variant="primary" onClick={onDone} trailing={<IconArrow />}>
          Open your dashboard
        </Button>
      </footer>
    </div>
  );
}
