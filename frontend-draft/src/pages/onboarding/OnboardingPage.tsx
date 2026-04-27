/**
 * OnboardingPage — section-by-section wizard with recap cards. /Oliviercontribution.
 *
 * Flow per Olivier: not "all 114 questions on one page" and not "just 3 phases".
 * Granular section navigation: user fills a section → recap card appears
 * showing every answer → "add more details" lets them inline-edit before
 * "Continue to next section". Phase-end shows a bigger recap. End of all 3
 * phases = "Your sales intelligence is ready" + jump to dashboard.
 *
 * Auto-save fires on every input change (debounced 600ms). Progress %
 * updates live from the backend response.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Badge,
  Button,
  Divider,
  PageHeader,
  Row,
  Stack,
  Surface,
  Text,
} from "@/design-system";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";
import { getSalesbookApi } from "@/shared/api/salesbook";
import type {
  OnboardingProgress,
  OnboardingResponse,
  Registry,
  RegistryQuestion,
} from "@/entities/salesbook/types";
import { QuestionInput } from "@/pages/onboarding/QuestionInput";

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
  // Sort questions within each section by `n`; sections by phase then first appearance
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
  const [recapOpen, setRecapOpen] = useState(false);
  const saveTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Initial fetch: registry + existing responses + progress
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

  if (!user) {
    navigate("/signup", { replace: true });
    return null;
  }

  if (loading || !registry) {
    return (
      <Stack gap="md">
        <PageHeader eyebrow="Onboarding" title="Loading your sales intelligence…" />
      </Stack>
    );
  }

  const sections = groupBySection(registry);
  const idx = Math.max(0, Math.min(sections.length - 1, Number(sectionIndex ?? "0")));
  const currentSection = sections[idx];
  const isLast = idx === sections.length - 1;

  const sectionQuestions = currentSection.questions;
  const answeredInSection = sectionQuestions.filter((q) => (responses[q.key] ?? "").trim() !== "").length;
  const sectionPct = Math.round((answeredInSection / sectionQuestions.length) * 100);

  function setAnswer(key: string, val: string, q: RegistryQuestion) {
    setResponses((prev) => ({ ...prev, [key]: val }));
    // Debounced save per question
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
        const fresh = await api.getOnboardingProgress(user!.profileId);
        setProgress(fresh);
      } catch (err) {
        console.warn("Save failed for", key, err);
      }
    }, 600);
    saveTimers.current.set(key, handle);
  }

  const goToSection = (n: number) => {
    setRecapOpen(false);
    navigate(`/onboarding/${n}`);
  };

  if (recapOpen) {
    return (
      <SectionRecap
        section={currentSection}
        responses={responses}
        onEdit={() => setRecapOpen(false)}
        onContinue={() => {
          if (isLast) {
            navigate("/dashboard", { replace: true });
          } else {
            goToSection(idx + 1);
          }
        }}
        isLast={isLast}
        nextSectionTitle={sections[idx + 1]?.section}
        progress={progress}
      />
    );
  }

  return (
    <Stack gap="md">
      <PageHeader
        eyebrow={`Phase ${currentSection.phase} · Section ${idx + 1} of ${sections.length}`}
        title={currentSection.section}
        description="Each section feeds your salesbook. Auto-saves as you type. Take your time — depth here = sharper agent context later."
      />

      <Row gap="sm" between baseline className="row--wrap">
        <Row gap="xs" baseline>
          <ProgressPill label="Phase 1" pct={pctNumber(progress?.phase1_pct)} />
          <ProgressPill label="Phase 2" pct={pctNumber(progress?.phase2_pct)} />
          <ProgressPill label="Phase 3" pct={pctNumber(progress?.phase3_pct)} />
        </Row>
        <Text variant="mono" className="text-body-muted">
          {answeredInSection}/{sectionQuestions.length} answered in this section ({sectionPct}%)
        </Text>
      </Row>

      <Surface padding="default">
        <Stack gap="md">
          {sectionQuestions.map((q) => (
            <QuestionInput
              key={q.key}
              question={q}
              value={responses[q.key] ?? ""}
              onChange={(v) => setAnswer(q.key, v, q)}
            />
          ))}
        </Stack>
      </Surface>

      <Row gap="sm" between className="row--wrap">
        <Button variant="ghost" onClick={() => idx > 0 && goToSection(idx - 1)} disabled={idx === 0}>
          ← Previous section
        </Button>
        <Button variant="primary" onClick={() => setRecapOpen(true)}>
          Recap this section →
        </Button>
      </Row>
    </Stack>
  );
}

function SectionRecap({
  section,
  responses,
  onEdit,
  onContinue,
  isLast,
  nextSectionTitle,
  progress,
}: {
  section: SectionGroup;
  responses: Record<string, string>;
  onEdit: () => void;
  onContinue: () => void;
  isLast: boolean;
  nextSectionTitle?: string;
  progress: OnboardingProgress | null;
}) {
  const answered = section.questions.filter((q) => (responses[q.key] ?? "").trim() !== "");
  const blank = section.questions.filter((q) => (responses[q.key] ?? "").trim() === "");

  return (
    <Stack gap="md">
      <PageHeader
        eyebrow={`Recap · Phase ${section.phase}`}
        title={`What we captured for "${section.section}"`}
        description="Anything to add or correct? Edit and we'll keep it. Otherwise continue — your sales agent gets smarter with every section you finish."
      />

      <Surface padding="default" tone="default">
        <Stack gap="sm">
          {answered.length === 0 ? (
            <Text className="text-body-muted">
              No answers yet for this section. Tap "Add details" to start filling it in.
            </Text>
          ) : (
            answered.map((q) => (
              <div key={q.key}>
                <div
                  className="text-body-muted text-mono"
                  style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" }}
                >
                  {q.question}
                </div>
                <div className="text-body" style={{ marginTop: 2 }}>
                  {responses[q.key]}
                </div>
              </div>
            ))
          )}
          {blank.length > 0 ? (
            <>
              <Divider />
              <Row gap="xs" baseline>
                <Badge tone="warn">{blank.length} unanswered</Badge>
                <Text variant="mono" className="text-body-muted">
                  ({blank.map((q) => q.question).slice(0, 2).join(" · ")}{blank.length > 2 ? " · …" : ""})
                </Text>
              </Row>
            </>
          ) : null}
        </Stack>
      </Surface>

      <Row gap="sm" between className="row--wrap">
        <Button variant="ghost" onClick={onEdit}>
          ← Add details
        </Button>
        <Button variant="primary" onClick={onContinue}>
          {isLast
            ? "Finish onboarding →"
            : `Continue to "${nextSectionTitle ?? "next section"}" →`}
        </Button>
      </Row>

      {progress ? (
        <Text variant="mono" className="text-body-muted">
          Overall: {pctNumber(progress.total_completion_pct).toFixed(1)}% complete
        </Text>
      ) : null}
    </Stack>
  );
}

function ProgressPill({ label, pct }: { label: string; pct: number }) {
  return (
    <Badge tone={pct >= 100 ? "success" : pct > 0 ? "info" : "outline"}>
      {label} · {pct.toFixed(0)}%
    </Badge>
  );
}
