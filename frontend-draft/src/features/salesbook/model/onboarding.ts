import type { Registry, RegistryQuestion } from "@/entities/salesbook/types";

export type SectionGroup = {
  phase: number;
  section: string;
  questions: RegistryQuestion[];
};

export function groupBySection(registry: Registry): SectionGroup[] {
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

export function pctNumber(value: number | string | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}