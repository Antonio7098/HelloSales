import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCurrentUser } from "@/shared/auth/useCurrentUser";
import { useAppData } from "@/shared/data/context";
import type {
  OnboardingProgress,
  Registry,
  RegistryQuestion,
} from "@/entities/salesbook/types";
import { groupBySection } from "../model/onboarding";

export function useOnboardingFlow() {
  const { user } = useCurrentUser();
  const navigate = useNavigate();
  const api = useAppData();

  const [registry, setRegistry] = useState<Registry | null>(null);
  const [ responses, setResponses] = useState<Record<string, string>>({});
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [showFinalRecap, setShowFinalRecap] = useState(false);
  const saveTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    async function load() {
      const [reg, existing, prog] = await Promise.all([
        api.getOnboardingRegistry(),
        api.listOnboardingResponses(user!.profileId),
        api.getOnboardingProgress(user!.profileId),
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

  function setAnswer(key: string, val: string, q: RegistryQuestion) {
    setResponses((prev) => ({ ...prev, [key]: val }));
    const existing = saveTimers.current.get(key);
    if (existing) clearTimeout(existing);
    const handle = setTimeout(async () => {
      try {
        await api.submitOnboardingResponse(user!.profileId, {
          phase: q.phase,
          question_key: key,
          response_value: val,
          response_type: q.answer_type ?? null,
          question_text: q.question ?? null,
        });
        const fresh = await api.getOnboardingProgress(user!.profileId);
        if (fresh) setProgress(fresh);
      } catch (err) {
        console.warn("Save failed for", key, err);
      }
    }, 600);
    saveTimers.current.set(key, handle);
  }

  function goToSection(idx: number) {
    navigate(`/onboarding/${idx}`);
  }

  function goToDashboard() {
    navigate("/dashboard", { replace: true });
  }

  if (!user) {
    navigate("/welcome", { replace: true });
    return null;
  }

  return {
    registry,
    responses,
    progress,
    loading,
    showFinalRecap,
    setShowFinalRecap,
    setAnswer,
    goToSection,
    goToDashboard,
    sections: registry ? groupBySection(registry) : [],
  };
}
