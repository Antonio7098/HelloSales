import { useEffect, useRef } from "react";
import { EmptyState } from "@/design-system/patterns/EmptyState";
import { Text } from "@/design-system/primitives/Text";
import { ChatMessage } from "@/features/chat/components/ChatMessage";
import { ToolActivity } from "@/features/chat/components/ToolActivity";
import type { SessionItem, StreamedAssistantDraft } from "@/features/chat/model/types";
import { buildTranscript, readText } from "@/features/chat/utils/session-items";

type ChatTranscriptProps = {
  items: SessionItem[];
  draft: StreamedAssistantDraft;
  hasSession: boolean;
  onPickStarter?: (prompt: string) => void;
  onApprovalDecision?: (approvalId: string, approved: boolean) => void;
  approvalDecisionById?: Record<string, boolean>;
};

const starters = [
  "Which substrate sections are still unanswered?",
  "Summarize the sales plan in three bullets.",
  "List every numeric prompt and their example answers.",
];

function formatTime(iso: string): string {
  try {
    const date = new Date(iso);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export function ChatTranscript({
  items,
  draft,
  hasSession,
  onPickStarter,
  onApprovalDecision,
  approvalDecisionById = {},
}: ChatTranscriptProps) {
  const entries = buildTranscript(items);
  const hasStreamingDraft = draft.turnId != null && draft.text.length > 0;
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [entries.length, draft.text, hasStreamingDraft]);

  if (!hasSession && entries.length === 0) {
    return (
      <div className="chat-transcript" ref={scrollRef}>
        <div style={{ maxWidth: "42rem" }}>
          <EmptyState
            eyebrow="Analyst ready"
            title="Start a conversation with the sales substrate."
            description="Every question routes through the approved SQL tool. Pick a starter or write your own — nothing is answered off-catalog."
          />
        </div>
        <div className="row row--wrap row--gap-sm" style={{ maxWidth: "42rem" }}>
          {starters.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="btn btn--subtle btn--sm"
              onClick={() => onPickStarter?.(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="chat-transcript" ref={scrollRef}>
      {entries.map((entry) => {
        if (entry.kind === "message") {
          const role = entry.item.item_type === "user_message" ? "user" : "assistant";
          return (
            <ChatMessage
              key={entry.key}
              role={role}
              content={readText(entry.item.payload)}
              timestamp={formatTime(entry.item.created_at)}
            />
          );
        }
        if (entry.kind === "tool") {
          const approvalId = typeof entry.call.payload.approval_id === "string" ? entry.call.payload.approval_id : null;
          return (
            <ToolActivity
              key={entry.key}
              call={entry.call}
              result={entry.result}
              onApprovalDecision={onApprovalDecision}
              approvalBusy={approvalId ? approvalDecisionById[approvalId] === true : false}
            />
          );
        }
        return (
          <div key={entry.key} className="msg msg--assistant">
            <div className="msg-role">System</div>
            <div className="msg-bubble text-body-muted">{readText(entry.item.payload) || entry.item.item_type}</div>
          </div>
        );
      })}

      {hasStreamingDraft ? (
        <ChatMessage role="assistant" content={draft.text} streaming />
      ) : null}

      {entries.length > 0 && !hasStreamingDraft ? (
        <Text variant="mono" className="text-body-muted" as="div">
          {/* subtle sentinel for accessibility, no visible marker */}
          <span className="sr-only">End of transcript</span>
        </Text>
      ) : null}
    </div>
  );
}
