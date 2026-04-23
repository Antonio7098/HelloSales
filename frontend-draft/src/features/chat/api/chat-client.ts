import { requestJson } from "@/shared/api/http-client";
import { getFrontendEnv } from "@/shared/config/env";
import type {
  ApprovalDecisionInput,
  ApiEnvelope,
  CreateChatSessionInput,
  SessionEvent,
  SessionItem,
  SessionSummary,
} from "@/features/chat/model/types";

const sessionStreamEventTypes = [
  "agent.tool.queued",
  "agent.approval.requested",
  "agent.tool.started",
  "agent.tool.failed",
  "agent.tool.completed",
  "agent.tool.cancelled",
  "agent.response.delta",
  "agent.turn.started",
  "agent.turn.awaiting_approval",
  "agent.turn.completed",
  "agent.turn.cancelled",
  "agent.turn.failed",
  "agent.approval.approved",
  "agent.approval.rejected",
  "agent.run.cancel_requested",
  "agent.run.cancelled",
] as const;

export async function createChatSession(input: CreateChatSessionInput): Promise<SessionSummary> {
  const response = await requestJson<ApiEnvelope<SessionSummary>>({
    path: "/sessions",
    method: "POST",
    body: JSON.stringify({
      input_text: input.inputText,
      profile_name: "generic",
      user_id: input.userId ?? null,
      org_id: input.orgId ?? null,
    }),
  });
  return response.data;
}

export async function appendChatMessage(sessionId: string, inputText: string): Promise<SessionSummary> {
  const response = await requestJson<ApiEnvelope<SessionSummary>>({
    path: `/sessions/${sessionId}/messages`,
    method: "POST",
    body: JSON.stringify({
      input_text: inputText,
    }),
  });
  return response.data;
}

export async function getSession(sessionId: string): Promise<SessionSummary> {
  const response = await requestJson<ApiEnvelope<SessionSummary>>({
    path: `/sessions/${sessionId}`,
  });
  return response.data;
}

export async function getSessionItems(sessionId: string): Promise<SessionItem[]> {
  const response = await requestJson<ApiEnvelope<SessionItem[]>>({
    path: `/sessions/${sessionId}/items`,
  });
  return response.data;
}

export async function decideSessionApproval(
  approvalId: string,
  input: ApprovalDecisionInput,
): Promise<SessionSummary> {
  const response = await requestJson<ApiEnvelope<SessionSummary>>({
    path: `/sessions/approvals/${approvalId}`,
    method: "POST",
    body: JSON.stringify({
      approved: input.approved,
    }),
  });
  return response.data;
}

export function subscribeToSessionEvents(
  sessionId: string,
  afterSequence: number,
  onEvent: (event: SessionEvent) => void,
): () => void {
  const url = new URL(
    `${getFrontendEnv().apiBaseUrl}/sessions/${sessionId}/events/stream`,
    window.location.origin,
  );
  url.searchParams.set("after_sequence", String(afterSequence));
  const source = new EventSource(url);
  const listeners = sessionStreamEventTypes.map((eventType) => {
    const listener = (message: MessageEvent<string>) => {
      onEvent(JSON.parse(message.data) as SessionEvent);
    };
    source.addEventListener(eventType, listener);
    return { eventType, listener };
  });

  return () => {
    listeners.forEach(({ eventType, listener }) => {
      source.removeEventListener(eventType, listener);
    });
    source.close();
  };
}
