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

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";
import { getSalesbookApi } from "@/shared/api/salesbook";
import { IconArrow, IconArrowLeft, IconCheck } from "@/shared/icons/NavIcons";
import type {
  OnboardingProgress,
  OnboardingResponse,
  Registry,
  RegistryQuestion,
} from "@/entities/salesbook/types";
import { QuestionInput } from "@/pages/onboarding/QuestionInput";
import { Button, Stack } from "@/design-system";

const QUESTIONS_PER_PAGE = 6; // long sections sub-page through groups of 6

type SectionGroup = {
  phase: number;
  section: string;
  questions: RegistryQuestion[];
};

function groupBySection(registry: Registry): SectionGroup[] {
  const groups = new Map<string, SectionGroup>();
  Object.values(registry).forEach((q) => {
    const key = `${q.phase}:::${q.section ?? "—"}`;
    if (!groups.has(key)) {
      groups.set(key, { phase: q.phase, section: q.section ?? "—", questions: [] });
    }
    groups.get(key)!.questions.push(q);
  });
  return Array.from(groups.values())
    .map((g) => ({ ...g, questions: g.questions.slice().sort((a, b) => a.n - b.n) }))
    .sort((a, b) => a.phase - b.phase || a.questions[0].n - b.questions[0].n);
}

function pctNumber(value: number | string | null | undefined): number {
  if (value === null || value === undefined) return 0;
  return typeof value === "number" ? value : Number(value);
}

export function OnboardingPage() {
  const { user } = useCurrentUser();
  const navigate = useNavigate();
  const { sectionIndex } = useParams<{ sectionIndex?: string }>();
  const api = useMemo(() => getSalesbookApi(), []);

  const [registry, setRegistry] = useState<Registry | null>(null);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [showFinalRecap, setShowFinalRecap] = useState(false);
  const [pageInSection, setPageInSection] = useState(0);
  const saveTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    async function load() {
      const [reg, existing, prog] = await Promise.all([
        api.getOnboardingRegistry(),
        api.listResponses(user!.profileId).catch(() => [] as OnboardingResponse[]),
        api.getOnboardingProgress(user!.profileId).catch(() => null),
      ]);
      if (cancelled) return;
      setRegistry(reg);
      const map: Record<string, string> = {};
      existing.forEach((r) => {
        if (r.response_value !== null) map[r.question_key] = r.response_value;
      });
      setResponses(map);
      if (prog) setProgress(prog);
      setLoading(false);
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [user, api]);

  // Reset sub-page when section changes
  useEffect(() => {
    setPageInSection(0);
  }, [sectionIndex]);

  if (!user) {
    navigate("/welcome", { replace: true });
    return null;
  }

  if (loading || !registry) {
    return (
      <div className="onboarding-loading">
        <div className="onboarding-eyebrow">Hello Sales · onboarding</div>
        <h1 className="onboarding-title">Loading your sales intelligence…</h1>
      </div>
    );
  }

  const sections = groupBySection(registry);
  const idx = Math.max(0, Math.min(sections.length - 1, Number(sectionIndex ?? "0")));
  const currentSection = sections[idx];

  // Sub-paginate long sections (best practice: divide rather than scroll-of-doom)
  const sectionQuestions = currentSection.questions;
  const totalSubPages = Math.max(1, Math.ceil(sectionQuestions.length / QUESTIONS_PER_PAGE));
  const safePage = Math.max(0, Math.min(totalSubPages - 1, pageInSection));
  const pageStart = safePage * QUESTIONS_PER_PAGE;
  const pageQuestions = sectionQuestions.slice(pageStart, pageStart + QUESTIONS_PER_PAGE);
  const isLastSubPage = safePage === totalSubPages - 1;
  const isFirstSubPage = safePage === 0;
  const isLastSection = idx === sections.length - 1;

  const answeredInSection = sectionQuestions.filter((q) => (responses[q.key] ?? "").trim() !== "").length;

  function setAnswer(key: string, val: string, q: RegistryQuestion) {
    setResponses((prev) => ({ ...prev, [key]: val }));
    const existing = saveTimers.current.get(key);
    if (existing) clearTimeout(existing);
    const handle = setTimeout(async () => {
      try {
        await api.submitResponse(user!.profileId, {
          phase: q.phase,
          question_key: key,
          response_value: val,
          response_type: q.answer_type ?? null,
          question_text: q.question ?? null,
        });
        const fresh = await api.getOnboardingProgress(user!.profileId).catch(() => null);
        if (fresh) setProgress(fresh);
      } catch (err) {
        console.warn("Save failed for", key, err);
      }
    }, 600);
    saveTimers.current.set(key, handle);
  }

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
    navigate(`/onboarding/${idx + 1}`);
  }

  function goToPrev() {
    if (!isFirstSubPage) {
      setPageInSection(safePage - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    if (idx > 0) {
      navigate(`/onboarding/${idx - 1}`);
    }
  }

  if (showFinalRecap) {
    return (
      <FinalRecap
        registry={registry}
        responses={responses}
        progress={progress}
        onBackToOnboarding={() => setShowFinalRecap(false)}
        onDone={() => navigate("/dashboard", { replace: true })}
      />
    );
  }

  return (
    <div className="onboarding-page">
      {/* Slim progress band */}
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

      {/* Section header — minimal, sets the stage */}
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

      {/* Questions — limited to QUESTIONS_PER_PAGE so the page never scrolls forever */}
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

      {/* Navigation */}
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

function PhaseDot({ label, active, pct }: { label: string; active: boolean; pct: number }) {
  const done = pct >= 100;
  return (
    <div className={`phase-dot ${active ? "is-active" : ""} ${done ? "is-done" : ""}`}>
      <span className="phase-dot-circle">
        {done ? <IconCheck width={12} height={12} /> : label}
      </span>
      <span className="phase-dot-label">Phase {label}</span>
      <span className="phase-dot-pct">{pct.toFixed(0)}%</span>
    </div>
  );
}

function FinalRecap({
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
  const totalAnswered = Object.values(responses).filter((v) => v.trim() !== "").length;
  const totalQuestions = Object.keys(registry).length;

  return (
    <div className="onboarding-final">
      <div className="onboarding-final-eyebrow">Hello Sales · your business IQ</div>
      <h1 className="onboarding-final-title">
        Here's what your sales agents now know.
      </h1>
      <p className="onboarding-final-sub">
        {totalAnswered} of {totalQuestions} questions answered
        {progress ? ` · ${pctNumber(progress.total_completion_pct).toFixed(0)}% complete` : ""}.
        This is the foundation every rep, every call, and every agent will draw from.
      </p>

      <div className="onboarding-final-body">
        {groups.map((g) => {
          const answered = g.questions.filter((q) => (responses[q.key] ?? "").trim() !== "");
          if (answered.length === 0) return null;
          return (
            <section key={`${g.phase}-${g.section}`} className="onboarding-final-section">
              <header className="onboarding-final-section-head">
                <span className="onboarding-final-section-phase">Phase {g.phase}</span>
                <h2 className="onboarding-final-section-title">{g.section}</h2>
                <span className="onboarding-final-section-count">
                  {answered.length}/{g.questions.length}
                </span>
              </header>
              <dl className="onboarding-final-list">
                {answered.map((q) => (
                  <div key={q.key} className="onboarding-final-item">
                    <dt>{q.question}</dt>
                    <dd>{responses[q.key]}</dd>
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
