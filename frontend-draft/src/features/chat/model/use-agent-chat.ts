import { useEffect, useState } from "react";
import {
  appendChatMessage,
  createChatSession,
  decideSessionApproval,
  getSessionEvents,
  getSession,
  getSessionItems,
  subscribeToSessionEvents,
} from "@/features/chat/api/chat-client";
import { ApiRequestError } from "@/shared/api/http-client";
import type {
  SessionEvent,
  SessionItem,
  SessionSummary,
  StreamedAssistantDraft,
} from "@/features/chat/model/types";

type AgentChatState = {
  session: SessionSummary | null;
  items: SessionItem[];
  events: SessionEvent[];
  streamedAssistantDraft: StreamedAssistantDraft;
  isConnecting: boolean;
  isSending: boolean;
  subscriptionNonce: number;
  approvalDecisionById: Record<string, boolean>;
  error: Error | null;
};

const initialState: AgentChatState = {
  session: null,
  items: [],
  events: [],
  streamedAssistantDraft: {
    turnId: null,
    text: "",
  },
  isConnecting: false,
  isSending: false,
  subscriptionNonce: 0,
  approvalDecisionById: {},
  error: null,
};

const terminalSessionStatuses = new Set(["completed", "failed", "cancelled"]);
const terminalEventTypes = new Set([
  "agent.turn.completed",
  "agent.turn.failed",
  "agent.turn.cancelled",
  "agent.run.cancelled",
]);
const pollIntervalMs = 2_000;
const stalledTurnWarningMs = 15_000;

function shouldClearDraft(items: SessionItem[], draft: StreamedAssistantDraft): boolean {
  return (
    draft.turnId != null &&
    items.some((item) => item.turn_id === draft.turnId && item.item_type === "assistant_message")
  );
}

function latestProgressAt(
  session: SessionSummary,
  items: SessionItem[],
  events: SessionEvent[],
): number {
  const timestamps = [Date.parse(session.updated_at)]
    .concat(items.map((item) => Date.parse(item.created_at)))
    .concat(events.map((event) => Date.parse(event.created_at)))
    .filter((value) => Number.isFinite(value));
  return timestamps.length > 0 ? Math.max(...timestamps) : Date.now();
}

function activeSessionWarning(
  session: SessionSummary,
  items: SessionItem[],
  events: SessionEvent[],
): Error | null {
  if (session.status !== "active") {
    return null;
  }
  if (Date.now() - latestProgressAt(session, items, events) < stalledTurnWarningMs) {
    return null;
  }
  return new Error(
    "The analyst is still marked active, but no new activity has arrived. This turn may be stalled.",
  );
}

function resolveSessionError(
  session: SessionSummary,
  items: SessionItem[],
  events: SessionEvent[],
  currentError: Error | null,
): Error | null {
  if (session.status === "failed") {
    return new Error(session.error_message ?? "The analyst failed to complete the turn.");
  }
  const warning = activeSessionWarning(session, items, events);
  if (warning !== null) {
    return warning;
  }
  if (currentError instanceof ApiRequestError) {
    return currentError;
  }
  return null;
}

function readCompletedAssistantItem(event: SessionEvent): SessionItem | null {
  if (event.event_type !== "agent.turn.completed") {
    return null;
  }
  const value = event.payload.assistant_item;
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const item = value as Partial<SessionItem>;
  if (
    typeof item.item_id !== "string" ||
    typeof item.sequence_no !== "number" ||
    item.item_type !== "assistant_message" ||
    typeof item.created_at !== "string" ||
    item.payload === null ||
    typeof item.payload !== "object" ||
    Array.isArray(item.payload)
  ) {
    return null;
  }
  return {
    item_id: item.item_id,
    sequence_no: item.sequence_no,
    item_type: item.item_type,
    actor_id: typeof item.actor_id === "string" ? item.actor_id : null,
    run_id: typeof item.run_id === "string" ? item.run_id : null,
    turn_id: typeof item.turn_id === "string" ? item.turn_id : null,
    tool_call_id: typeof item.tool_call_id === "string" ? item.tool_call_id : null,
    payload: item.payload as Record<string, unknown>,
    created_at: item.created_at,
  };
}

function upsertSessionItem(items: SessionItem[], item: SessionItem): SessionItem[] {
  const existingIndex = items.findIndex((candidate) => candidate.item_id === item.item_id);
  if (existingIndex >= 0) {
    const next = [...items];
    next[existingIndex] = item;
    return next;
  }
  return [...items, item].sort((left, right) => left.sequence_no - right.sequence_no);
}

export function useAgentChat() {
  const [state, setState] = useState<AgentChatState>(initialState);

  useEffect(() => {
    if (!state.session) {
      return;
    }
    if (terminalSessionStatuses.has(state.session.status)) {
      return;
    }

    const sessionId = state.session.session_id;
    const lastSequence = state.events.at(-1)?.sequence_no ?? 0;
    let isClosed = false;

    async function refreshSessionState({ force = false }: { force?: boolean } = {}) {
      try {
        const [session, items, events] = await Promise.all([
          getSession(sessionId),
          getSessionItems(sessionId),
          getSessionEvents(sessionId),
        ]);
        if (isClosed && !force) {
          return;
        }
        setState((current) => {
          if (current.session?.session_id !== sessionId) {
            return current;
          }
          return {
            ...current,
            session,
            items,
            events,
            streamedAssistantDraft: shouldClearDraft(items, current.streamedAssistantDraft)
              ? { turnId: null, text: "" }
              : current.streamedAssistantDraft,
            error: resolveSessionError(session, items, events, current.error),
          };
        });
      } catch {
        // Keep the current transcript if the post-event refresh fails.
      }
    }

    let unsubscribe = () => {};
    unsubscribe = subscribeToSessionEvents(sessionId, lastSequence, (event) => {
      setState((current) => {
        const latestSequence = current.events.at(-1)?.sequence_no ?? 0;
        const alreadySeen =
          current.events.some((existing) => existing.event_id === event.event_id) ||
          event.sequence_no <= latestSequence;
        if (alreadySeen) {
          return current;
        }

        const eventTurnId = typeof event.payload.turn_id === "string" ? event.payload.turn_id : event.turn_id;
        const completedAssistantItem = readCompletedAssistantItem(event);
        const items =
          completedAssistantItem === null
            ? current.items
            : upsertSessionItem(current.items, completedAssistantItem);
        const hasPersistedTurn =
          eventTurnId != null && items.some((item) => item.turn_id === eventTurnId && item.item_type === "assistant_message");

        let streamedAssistantDraft = current.streamedAssistantDraft;
        if (event.event_type === "agent.turn.started") {
          streamedAssistantDraft = { turnId: null, text: "" };
        } else if (event.event_type === "agent.response.delta") {
          const delta = typeof event.payload.delta === "string" ? event.payload.delta : "";
          const nextTurnId = eventTurnId ?? current.streamedAssistantDraft.turnId;
          streamedAssistantDraft =
            nextTurnId == null || hasPersistedTurn
              ? { turnId: null, text: "" }
              : {
                  turnId: nextTurnId,
                  text:
                    current.streamedAssistantDraft.turnId === nextTurnId
                      ? current.streamedAssistantDraft.text + delta
                      : delta,
                };
        } else if (
          (event.event_type === "agent.turn.failed" || event.event_type === "agent.turn.cancelled") &&
          eventTurnId != null &&
          current.streamedAssistantDraft.turnId === eventTurnId
        ) {
          streamedAssistantDraft = { turnId: null, text: "" };
        }

        return {
          ...current,
          items,
          events: [...current.events, event],
          streamedAssistantDraft,
          error:
            event.event_type === "agent.turn.failed"
              ? new Error(
                  typeof (event.payload.error as { message?: unknown } | undefined)?.message === "string"
                    ? ((event.payload.error as { message: string }).message)
                    : "The analyst failed to complete the turn.",
                )
              : null,
        };
      });

      if (
        event.event_type === "agent.turn.awaiting_approval" ||
        event.event_type === "agent.turn.completed" ||
        event.event_type === "agent.turn.failed" ||
        event.event_type === "agent.turn.cancelled" ||
        event.event_type === "agent.approval.approved" ||
        event.event_type === "agent.approval.rejected" ||
        event.event_type === "agent.tool.completed" ||
        event.event_type === "agent.tool.failed"
      ) {
        void refreshSessionState({ force: terminalEventTypes.has(event.event_type) });
      }

      if (terminalEventTypes.has(event.event_type)) {
        isClosed = true;
        unsubscribe();
      }
    });

    const pollHandle = window.setInterval(() => {
      void refreshSessionState();
    }, pollIntervalMs);

    return () => {
      isClosed = true;
      window.clearInterval(pollHandle);
      unsubscribe();
    };
  }, [state.session?.session_id, state.session?.status, state.subscriptionNonce]);

  async function startSession(inputText: string) {
    setState((current) => ({
      ...current,
      isConnecting: true,
      error: null,
    }));
    try {
      const session = await createChatSession({ inputText });
      const items = await getSessionItems(session.session_id);
      setState((current) => ({
        session,
        items,
        events: current.session?.session_id === session.session_id ? current.events : [],
        streamedAssistantDraft:
          current.session?.session_id === session.session_id && !shouldClearDraft(items, current.streamedAssistantDraft)
            ? current.streamedAssistantDraft
            : {
                turnId: null,
                text: "",
              },
        isConnecting: false,
        isSending: false,
        subscriptionNonce: current.subscriptionNonce + 1,
        approvalDecisionById: {},
        error: null,
      }));
      return session;
    } catch (error) {
      const resolvedError = error instanceof Error ? error : new Error("Failed to create chat session");
      setState((current) => ({
        ...current,
        isConnecting: false,
        error: resolvedError,
      }));
      throw resolvedError;
    }
  }

  async function sendMessage(inputText: string) {
    if (!state.session) {
      return startSession(inputText);
    }

    setState((current) => ({
      ...current,
      isSending: true,
      error: null,
    }));
    try {
      const session = await appendChatMessage(state.session.session_id, inputText);
      const items = await getSessionItems(session.session_id);
      setState((current) => ({
        ...current,
        session,
        items,
        subscriptionNonce: current.subscriptionNonce + 1,
        streamedAssistantDraft: shouldClearDraft(items, current.streamedAssistantDraft)
          ? { turnId: null, text: "" }
          : current.streamedAssistantDraft,
        isSending: false,
        error: null,
      }));
      return session;
    } catch (error) {
      if (state.session) {
        try {
          const [session, items, events] = await Promise.all([
            getSession(state.session.session_id),
            getSessionItems(state.session.session_id),
            getSessionEvents(state.session.session_id),
          ]);
          const resolvedError = error instanceof Error ? error : new Error("Failed to send chat message");
          setState((current) => ({
            ...current,
            session,
            items,
            events,
            isSending: false,
            error: resolveSessionError(session, items, events, resolvedError),
          }));
          throw resolvedError;
        } catch {
          // Fall through to the original transport error if the recovery refresh fails.
        }
      }
      const resolvedError = error instanceof Error ? error : new Error("Failed to send chat message");
      setState((current) => ({
        ...current,
        isSending: false,
        error: resolvedError,
      }));
      throw resolvedError;
    }
  }

  async function respondToApproval(approvalId: string, approved: boolean) {
    const sessionId = state.session?.session_id;
    if (!sessionId) {
      throw new Error("Cannot submit an approval decision without an active session");
    }
    setState((current) => ({
      ...current,
      approvalDecisionById: {
        ...current.approvalDecisionById,
        [approvalId]: true,
      },
      error: null,
    }));
    try {
      await decideSessionApproval(approvalId, { approved });
      const [session, items, events] = await Promise.all([
        getSession(sessionId),
        getSessionItems(sessionId),
        getSessionEvents(sessionId),
      ]);
      setState((current) => {
        const nextDecisionState = { ...current.approvalDecisionById };
        delete nextDecisionState[approvalId];
        return {
          ...current,
          session,
          items,
          events,
          subscriptionNonce: current.subscriptionNonce + 1,
          approvalDecisionById: nextDecisionState,
          error: resolveSessionError(session, items, events, null),
        };
      });
      return session;
    } catch (error) {
      const resolvedError = error instanceof Error ? error : new Error("Failed to submit approval decision");
      setState((current) => {
        const nextDecisionState = { ...current.approvalDecisionById };
        delete nextDecisionState[approvalId];
        return {
          ...current,
          approvalDecisionById: nextDecisionState,
          error: resolvedError,
        };
      });
      throw resolvedError;
    }
  }

  return {
    ...state,
    startSession,
    sendMessage,
    respondToApproval,
  };
}
