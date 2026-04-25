import { Badge } from "@/design-system/primitives/Badge";
import { StatusDot } from "@/design-system/primitives/StatusDot";
import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";
import { PageHeader } from "@/design-system/patterns/PageHeader";
import { ChatTranscript } from "@/features/chat/components/ChatTranscript";
import { Composer } from "@/features/chat/components/Composer";
import { SessionSummaryPanel } from "@/features/chat/components/SessionSummary";
import { useAgentChat } from "@/features/chat/model/use-agent-chat";

export function ChatWorkspace() {
  const chat = useAgentChat();
  const {
    session,
    items,
    events,
    streamedAssistantDraft,
    isConnecting,
    isSending,
    approvalDecisionById,
    error,
  } = chat;
  const statusBusy =
    isConnecting ||
    isSending ||
    session?.status === "active" ||
    session?.status === "awaiting_approval";
  const composerBusy = isConnecting || isSending;

  async function handleSubmit(text: string) {
    await chat.sendMessage(text);
  }

  const tone = error ? "danger" : statusBusy ? "warn" : session ? "success" : "neutral";

  return (
    <>
      <PageHeader
        eyebrow="Analyst workspace"
        title={
          <>
            Ask the <em>substrate</em> anything.
          </>
        }
        description="A governed dashboard analyst. It reads only the approved SQL tool and streams answers as it thinks."
        actions={
          <Badge tone={tone}>
            <StatusDot tone={tone} pulse={statusBusy} />
            {error
              ? "Error"
              : statusBusy
                ? isSending
                  ? "Replying"
                  : session?.status === "awaiting_approval"
                    ? "Awaiting approval"
                    : session?.status === "active"
                      ? "Working"
                      : "Connecting"
                : session
                  ? "Ready"
                  : "Idle"}
          </Badge>
        }
      />

      {error ? (
        <Surface tone="bare" className="row row--gap-sm" padding="tight">
          <StatusDot tone="danger" />
          <Text variant="bodyStrong">Runtime error</Text>
          <Text variant="bodyMuted" className="text-mono">
            {error.message}
          </Text>
        </Surface>
      ) : null}

      <div className="chat-workspace">
        <Surface padding="flush" className="chat-main">
          <header className="chat-header">
            <div className="row row--gap-sm">
              <Text variant="sectionTitle">Transcript</Text>
              <Badge tone="outline">profile · generic</Badge>
            </div>
            <Text variant="mono" className="text-body-muted">
              {items.length} turn{items.length === 1 ? "" : "s"}
            </Text>
          </header>

          <ChatTranscript
            items={items}
            draft={streamedAssistantDraft}
            hasSession={Boolean(session)}
            approvalDecisionById={approvalDecisionById}
            onPickStarter={(prompt) => {
              void chat.sendMessage(prompt);
            }}
            onApprovalDecision={(approvalId, approved) => {
              void chat.respondToApproval(approvalId, approved);
            }}
          />

          <Composer
            onSubmit={handleSubmit}
            busy={composerBusy}
            disabled={Boolean(error) && !session}
          />
        </Surface>

        <SessionSummaryPanel
          session={session}
          events={events}
          isConnecting={isConnecting}
          error={error}
        />
      </div>
    </>
  );
}
