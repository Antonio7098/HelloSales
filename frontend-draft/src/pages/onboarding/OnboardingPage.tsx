/**
 * OnboardingPage — one question at a time. /Oliviercontribution.
 *
 * Modern beige canvas, black question prominent on top, a single input below,
 * Back / Next at the bottom. Every answer auto-saves. At the end, the answers
 * are rolled up into the company Salesbook (final recap → "create your
 * company salesbook").
 *
 * Drives off a flat, ordered list of all registry questions (phase + section
 * are shown as context above each question) rather than per-section routing.
 */

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { FinalRecap, pctNumber, useOnboardingFlow } from "@/features/salesbook";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";
import { IconArrow, IconArrowLeft } from "@/shared/icons/NavIcons";
import { QuestionInput } from "@/pages/onboarding/QuestionInput";
import type { RegistryQuestion } from "@/entities/salesbook/types";

/**
 * Persist the full answer set to git (via the Vercel serverless function).
 * Best-effort: on local dev (/api not running) or any failure it silently
 * no-ops — the answers are already in the demo store from per-question saves.
 */
async function persistToGit(
  user: { profileId: string; name: string; email: string; companyName: string; role: string } | null,
  questions: RegistryQuestion[],
  responses: Record<string, string>,
  progress: { total_completion_pct?: number | string | null } | null,
) {
  if (!user) return;
  const payload = {
    profileId: user.profileId,
    name: user.name,
    email: user.email,
    companyName: user.companyName,
    role: user.role,
    progress,
    responses: questions.map((q) => ({
      phase: q.phase,
      question_key: q.key,
      question_text: q.question ?? null,
      response_value: responses[q.key] ?? "",
      response_type: q.answer_type ?? null,
    })),
  };
  try {
    await fetch("/api/save-onboarding", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn("[onboarding] git save skipped:", err);
  }
}

const PHASE_LABEL: Record<number, string> = {
  1: "Phase 1 · Company Onboarding",
  2: "Phase 2 · Sales Book",
  3: "Phase 3 · VP Conversion",
};

export function OnboardingPage() {
  const navigate = useNavigate();
  const flow = useOnboardingFlow();
  const { user } = useCurrentUser();
  const [index, setIndex] = useState(0);
  const [started, setStarted] = useState(false);

  // Flat, ordered question list across all sections.
  const questions: RegistryQuestion[] = useMemo(() => {
    if (!flow || !flow.sections) return [];
    return flow.sections.flatMap((s) =>
      s.questions.map((q) => ({ ...q, phase: s.phase, section: s.section })),
    );
  }, [flow]);

  // On first load, jump to the first unanswered question (resume where you left off).
  useEffect(() => {
    if (started || questions.length === 0 || !flow) return;
    const firstUnanswered = questions.findIndex(
      (q) => (flow.responses[q.key] ?? "").trim() === "",
    );
    setIndex(firstUnanswered === -1 ? 0 : firstUnanswered);
    setStarted(true);
  }, [questions, flow, started]);

  if (flow === null) return null;

  const {
    loading,
    progress,
    registry,
    responses,
    setAnswer,
    showFinalRecap,
    setShowFinalRecap,
  } = flow;

  if (loading || !registry || questions.length === 0) {
    return (
      <div className="onboarding-loading">
        <div className="onboarding-eyebrow">Hello Sales · onboarding</div>
        <h1 className="onboarding-title">Loading your sales intelligence…</h1>
      </div>
    );
  }

  if (showFinalRecap) {
    return (
      <FinalRecap
        registry={registry}
        responses={responses}
        progress={progress}
        onBackToOnboarding={() => setShowFinalRecap(false)}
        onDone={() => navigate("/salesbook", { replace: true })}
      />
    );
  }

  const total = questions.length;
  const safeIndex = Math.max(0, Math.min(total - 1, index));
  const q = questions[safeIndex];
  const isFirst = safeIndex === 0;
  const isLast = safeIndex === total - 1;
  const answeredCount = questions.filter((x) => (responses[x.key] ?? "").trim() !== "").length;
  const barPct = Math.round(((safeIndex + 1) / total) * 100);

  function goNext() {
    if (isLast) {
      // Publish the completed answer set to the git-backed store, then recap.
      void persistToGit(user, questions, responses, progress);
      setShowFinalRecap(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    setIndex(safeIndex + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function goPrev() {
    if (isFirst) return;
    setIndex(safeIndex - 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    goNext();
  }

  return (
    <div className="onboarding-q">
      {/* Progress */}
      <div className="onboarding-q-progressbar" aria-hidden="true">
        <span style={{ width: `${barPct}%` }} />
      </div>
      <div className="onboarding-q-meta">
        <span className="onboarding-q-count">Question {safeIndex + 1} of {total}</span>
        <span className="onboarding-q-overall">
          {pctNumber(progress?.total_completion_pct).toFixed(0)}% complete · {answeredCount}/{total} answered · auto-saved
        </span>
      </div>

      {/* The question — black, big, on top */}
      <form className="onboarding-q-card" onSubmit={handleSubmit}>
        <div className="onboarding-q-context">
          {PHASE_LABEL[q.phase] ?? `Phase ${q.phase}`}
          {q.section ? ` · ${q.section}` : ""}
          {q.subsection ? ` · ${q.subsection}` : ""}
        </div>

        <h1 className="onboarding-q-text">{q.question}</h1>

        {q.example ? (
          <p className="onboarding-q-example">e.g. {q.example}</p>
        ) : null}

        <div className="onboarding-q-control">
          <QuestionInput
            key={q.key}
            question={q}
            value={responses[q.key] ?? ""}
            onChange={(v) => setAnswer(q.key, v, q)}
            hideLabel
          />
        </div>

        <div className="onboarding-q-footer">
          <button
            type="button"
            className="onboarding-q-back"
            onClick={goPrev}
            disabled={isFirst}
          >
            <IconArrowLeft /> Back
          </button>

          <button type="submit" className="onboarding-q-next">
            {isLast ? "Create my salesbook" : "Next"} <IconArrow />
          </button>
        </div>
      </form>

      <button
        type="button"
        className="onboarding-q-skip"
        onClick={goNext}
      >
        {isLast ? "Finish" : "Skip for now"}
      </button>
    </div>
  );
}
