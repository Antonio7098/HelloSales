import type { SessionItem } from "@/features/chat/model/types";

export type ToolInvocation = {
  kind: "tool";
  key: string;
  call: SessionItem;
  result: SessionItem | null;
};

export type MessageEntry = {
  kind: "message";
  key: string;
  item: SessionItem;
};

export type SystemEntry = {
  kind: "system";
  key: string;
  item: SessionItem;
};

export type TranscriptEntry = MessageEntry | ToolInvocation | SystemEntry;

/**
 * Collapse raw session items into a transcript-friendly sequence where a tool_call
 * and its matching tool_result render as a single invocation.
 */
export function buildTranscript(items: SessionItem[]): TranscriptEntry[] {
  const consumedResults = new Set<string>();
  const entries: TranscriptEntry[] = [];

  for (const item of items) {
    if (item.item_type === "tool_result") {
      if (consumedResults.has(item.item_id)) continue;
      entries.push({ kind: "tool", key: item.item_id, call: item, result: item });
      continue;
    }

    if (item.item_type === "tool_call") {
      const pairedResult = findMatchingResult(items, item);
      if (pairedResult) consumedResults.add(pairedResult.item_id);
      entries.push({
        kind: "tool",
        key: item.tool_call_id ?? item.item_id,
        call: item,
        result: pairedResult,
      });
      continue;
    }

    if (item.item_type === "user_message" || item.item_type === "assistant_message") {
      entries.push({ kind: "message", key: item.item_id, item });
      continue;
    }

    entries.push({ kind: "system", key: item.item_id, item });
  }

  return entries;
}

function findMatchingResult(items: SessionItem[], call: SessionItem): SessionItem | null {
  if (!call.tool_call_id) return null;
  return (
    items.find(
      (candidate) =>
        candidate.item_type === "tool_result" && candidate.tool_call_id === call.tool_call_id,
    ) ?? null
  );
}

export function readText(payload: Record<string, unknown>): string {
  const text = payload.text;
  return typeof text === "string" ? text : "";
}

export function readString(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" ? value : null;
}

export function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
