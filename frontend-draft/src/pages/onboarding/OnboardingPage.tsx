/**
 * OnboardingPage — section-by-section, focus-mode wizard. /Oliviercontribution.
 *
 * One section per page. Question/answer only — no app sidebar. Long sections
 * are sub-paged (page through groups of ~6 questions) instead of one giant
 * scroll. Auto-save on every change. Final recap appears ONLY at the very end
 * (when the wizard has actually built something worth showing).
 *
 * Section navigation lives at the bottom (Prev/Next) with a slim phase-progress
 * indicator at the top.
 */

import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FinalRecap, PhaseDot, pctNumber, useOnboardingFlow } from "@/features/salesbook";
import { IconArrow, IconArrowLeft } from "@/shared/icons/NavIcons";
import { QuestionInput } from "@/pages/onboarding/QuestionInput";
import { Button, Stack } from "@/design-system";

const QUESTIONS_PER_PAGE = 6;

export function OnboardingPage() {
  const navigate = useNavigate();
  const { sectionIndex } = useParams<{ sectionIndex?: string }>();
  const flow = useOnboardingFlow();
  const [pageInSection, setPageInSection] = useState(0);

  useEffect(() => {
    setPageInSection(0);
  }, [sectionIndex]);

  if (flow === null) {
    return null;
  }

  const {
    loading,
    progress,
    registry,
    responses,
    sections,
    setAnswer,
    showFinalRecap,
    setShowFinalRecap,
    goToDashboard,
    goToSection,
  } = flow;

  if (loading || !registry) {
    return (
      <div className="onboarding-loading">
        <div className="onboarding-eyebrow">Hello Sales · onboarding</div>
        <h1 className="onboarding-title">Loading your sales intelligence…</h1>
      </div>
    );
  }

  const idx = Math.max(0, Math.min(sections.length - 1, Number(sectionIndex ?? "0")));
  const currentSection = sections[idx];

  const sectionQuestions = currentSection.questions;
  const totalSubPages = Math.max(1, Math.ceil(sectionQuestions.length / QUESTIONS_PER_PAGE));
  const safePage = Math.max(0, Math.min(totalSubPages - 1, pageInSection));
  const pageStart = safePage * QUESTIONS_PER_PAGE;
  const pageQuestions = sectionQuestions.slice(pageStart, pageStart + QUESTIONS_PER_PAGE);
  const isLastSubPage = safePage === totalSubPages - 1;
  const isFirstSubPage = safePage === 0;
  const isLastSection = idx === sections.length - 1;

  const answeredInSection = sectionQuestions.filter((q) => (responses[q.key] ?? "").trim() !== "").length;

  function goToNext() {
    if (!isLastSubPage) {
      setPageInSection(safePage + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    if (isLastSection) {
      setShowFinalRecap(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    goToSection(idx + 1);
  }

  function goToPrev() {
    if (!isFirstSubPage) {
      setPageInSection(safePage - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    if (idx > 0) {
      goToSection(idx - 1);
    }
  }

  if (showFinalRecap) {
    return (
      <FinalRecap
        registry={registry}
        responses={responses}
        progress={progress}
        onBackToOnboarding={() => setShowFinalRecap(false)}
        onDone={goToDashboard}
      />
    );
  }

  return (
    <div className="onboarding-page">
      <div className="onboarding-progress">
        <div className="onboarding-progress-phases">
          <PhaseDot
            label="1"
            active={currentSection.phase === 1}
            pct={pctNumber(progress?.phase1_pct)}
          />
          <PhaseDot
            label="2"
            active={currentSection.phase === 2}
            pct={pctNumber(progress?.phase2_pct)}
          />
          <PhaseDot
            label="3"
            active={currentSection.phase === 3}
            pct={pctNumber(progress?.phase3_pct)}
          />
        </div>
        <div className="onboarding-progress-meta">
          Section {idx + 1} / {sections.length}
          {totalSubPages > 1 ? ` · page ${safePage + 1} / ${totalSubPages}` : null}
          {" · "}
          {answeredInSection}/{sectionQuestions.length} answered
        </div>
      </div>

      <header className="onboarding-section-header">
        <div className="onboarding-eyebrow">
          Phase {currentSection.phase}
          {currentSection.questions[0]?.subsection
            ? ` · ${currentSection.questions[0].subsection}`
            : null}
        </div>
        <h1 className="onboarding-title">{currentSection.section}</h1>
        <p className="onboarding-sub">
          Take your time. The depth here is what makes your sales agents sharp downstream.
        </p>
      </header>

      <Stack gap="lg">
        {pageQuestions.map((q) => (
          <QuestionInput
            key={q.key}
            question={q}
            value={responses[q.key] ?? ""}
            onChange={(v) => setAnswer(q.key, v, q)}
          />
        ))}
      </Stack>

      <footer className="onboarding-footer">
        <Button variant="ghost" onClick={goToPrev} disabled={idx === 0 && isFirstSubPage} leading={<IconArrowLeft />}>
          Previous
        </Button>
        <div className="onboarding-footer-meta">
          {pctNumber(progress?.total_completion_pct).toFixed(0)}% complete · auto-saved
        </div>
        <Button variant="primary" onClick={goToNext} trailing={<IconArrow />}>
          {!isLastSubPage
            ? "Continue"
            : isLastSection
              ? "Finish onboarding"
              : `Next: ${sections[idx + 1].section}`}
        </Button>
      </footer>
    </div>
  );
}
