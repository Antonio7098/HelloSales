import { Button } from "@/design-system/primitives/Button";
import { Badge } from "@/design-system/primitives/Badge";
import type { BadgeTone } from "@/design-system/primitives/Badge";
import { StatusDot } from "@/design-system/primitives/StatusDot";
import type { SessionItem } from "@/features/chat/model/types";
import { prettyJson, readString } from "@/features/chat/utils/session-items";

type ToolActivityProps = {
  call: SessionItem;
  result: SessionItem | null;
  onApprovalDecision?: (approvalId: string, approved: boolean) => void;
  approvalBusy?: boolean;
};

type ToolTone = Exclude<BadgeTone, "outline">;

const statusTone: Record<string, ToolTone> = {
  pending: "warn",
  pending_approval: "warn",
  queued: "warn",
  running: "info",
  awaiting_approval: "warn",
  completed: "success",
  succeeded: "success",
  failed: "danger",
  error: "danger",
  cancelled: "neutral",
};

export function ToolActivity({ call, result, onApprovalDecision, approvalBusy = false }: ToolActivityProps) {
  const toolName = readString(call.payload, "tool_name") ?? "unknown tool";
  const callStatus = readString(call.payload, "status") ?? "queued";
  const resolvedStatus = result ? (readString(result.payload, "status") ?? callStatus) : callStatus;
  const tone = statusTone[resolvedStatus] ?? "neutral";
  const approvalId = readString(call.payload, "approval_id");
  const requiresApproval = call.payload.requires_approval === true;
  const canDecideApproval =
    requiresApproval &&
    (resolvedStatus === "awaiting_approval" || resolvedStatus === "pending_approval") &&
    typeof approvalId === "string";

  const args = call.payload.arguments;
  const resultPayload = result?.payload.result;
  const errorMessage = result ? readString(result.payload, "error_message") : null;

  return (
    <article className="tool-card">
      <header className="tool-card-head">
        <span className="tool-card-name">
          <StatusDot tone={tone} pulse={resolvedStatus === "running" || resolvedStatus === "queued"} />
          {toolName}
        </span>
        <Badge tone={tone}>{resolvedStatus}</Badge>
      </header>
      <details>
        <summary>Arguments</summary>
        <div className="tool-card-body">
          <pre>{prettyJson(args ?? {})}</pre>
        </div>
      </details>
      {canDecideApproval ? (
        <div className="row row--wrap row--gap-sm" style={{ marginTop: "0.75rem" }}>
          <Button
            variant="primary"
            size="sm"
            disabled={approvalBusy}
            onClick={() => onApprovalDecision?.(approvalId, true)}
          >
            {approvalBusy ? "Submitting…" : "Approve query"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={approvalBusy}
            onClick={() => onApprovalDecision?.(approvalId, false)}
          >
            Reject
          </Button>
        </div>
      ) : null}
      {result ? (
        <details open={resolvedStatus === "failed" || resolvedStatus === "error"}>
          <summary>{errorMessage ? "Error" : "Result"}</summary>
          <div className="tool-card-body">
            <pre>{errorMessage ?? prettyJson(resultPayload ?? {})}</pre>
          </div>
        </details>
      ) : null}
    </article>
  );
}
