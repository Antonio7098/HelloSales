import type { BadgeTone } from "@/design-system/primitives/Badge";

export function formatAnswerType(answerType: string): string {
  return answerType.replace(/_/g, " ").toLowerCase();
}

const toneByType: Record<string, BadgeTone> = {
  text: "neutral",
  number: "info",
  integer: "info",
  decimal: "info",
  currency: "accent",
  percent: "accent",
  date: "warn",
  enum: "success",
  boolean: "success",
  list: "outline",
};

export function answerTypeTone(answerType: string): BadgeTone {
  const key = answerType.toLowerCase();
  return toneByType[key] ?? "neutral";
}
