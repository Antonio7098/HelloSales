import { Badge } from "@/design-system/primitives/Badge";
import { StatusDot } from "@/design-system/primitives/StatusDot";
import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";
import { DefinitionList } from "@/design-system/patterns/DefinitionList";
import type { SessionEvent, SessionSummary as SessionView } from "@/features/chat/model/types";

type SessionSummaryProps = {
  session: SessionView | null;
  events: SessionEvent[];
  isConnecting: boolean;
  error: Error | null;
};

function short(id: string | null): string {
  if (!id) return "—";
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}

export function SessionSummaryPanel({ session, events, isConnecting, error }: SessionSummaryProps) {
  const statusTone = error
    ? "danger"
    : isConnecting
      ? "warn"
      : session
        ? "success"
        : "neutral";

  return (
    <aside className="chat-side">
      <Surface tone="bare" padding="tight" className="side-section">
        <div className="row row--between">
          <Text variant="eyebrow">Session</Text>
          <Badge tone={statusTone}>
            <StatusDot tone={statusTone} pulse={isConnecting} />
            {error ? "Error" : isConnecting ? "Connecting" : session ? "Streaming" : "Idle"}
          </Badge>
        </div>
        <DefinitionList
          items={[
            { term: "ID", description: <code className="text-mono">{short(session?.session_id ?? null)}</code> },
            { term: "Profile", description: session?.profile_name ?? "generic" },
            { term: "Status", description: session?.status ?? "not started" },
            { term: "Updated", description: session ? formatTime(session.updated_at) : "—" },
          ]}
        />
      </Surface>

      <Surface tone="bare" padding="tight" className="side-section">
        <Text variant="eyebrow">Recent events</Text>
        {events.length === 0 ? (
          <Text variant="bodyMuted" className="text-mono">
            No runtime events yet.
          </Text>
        ) : (
          <ul className="stack-2xs" style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {events.slice(-8).reverse().map((event) => (
              <li key={event.event_id} className="row row--between row--gap-sm">
                <span className="text-mono" style={{ color: "var(--ink)", fontSize: "0.78rem" }}>
                  {event.event_type.replace(/^agent\./, "")}
                </span>
                <span className="text-mono text-body-muted" style={{ fontSize: "0.72rem" }}>
                  {formatTime(event.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Surface>

      <Surface tone="bare" padding="tight" className="side-section">
        <Text variant="eyebrow">Guardrails</Text>
        <Text variant="bodyMuted" className="text-mono">
          The analyst is restricted to the governed SQL tool against
          <code className="text-mono"> dashboard_data_entries</code>. No free-form database access.
        </Text>
      </Surface>
    </aside>
  );
}
