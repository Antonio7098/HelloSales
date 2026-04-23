import { useEffect, useState } from "react";
import {
  appendChatMessage,
  createChatSession,
  decideSessionApproval,
  getSession,
  getSessionItems,
  subscribeToSessionEvents,
} from "@/features/chat/api/chat-client";
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

    async function refreshSessionState() {
      try {
        const [session, items] = await Promise.all([getSession(sessionId), getSessionItems(sessionId)]);
        if (isClosed) {
          return;
        }
        setState((current) => {
          if (current.session?.session_id !== sessionId) {
            return current;
          }
          const draftTurnId = current.streamedAssistantDraft.turnId;
          const hasMatchingItem =
            draftTurnId != null && items.some((item: SessionItem) => item.turn_id === draftTurnId);
          return {
            ...current,
            session,
            items,
            streamedAssistantDraft: hasMatchingItem
              ? { turnId: null, text: "" }
              : current.streamedAssistantDraft,
            error:
              session.status === "failed"
                ? new Error(session.error_message ?? "The analyst failed to complete the turn.")
                : current.error,
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
        const hasPersistedTurn =
          eventTurnId != null && current.items.some((item) => item.turn_id === eventTurnId && item.item_type === "assistant_message");

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
          (event.event_type === "agent.turn.completed" ||
            event.event_type === "agent.turn.awaiting_approval" ||
            event.event_type === "agent.turn.failed" ||
            event.event_type === "agent.turn.cancelled") &&
          eventTurnId != null &&
          current.streamedAssistantDraft.turnId === eventTurnId
        ) {
          streamedAssistantDraft = { turnId: null, text: "" };
        }

        return {
          ...current,
          events: [...current.events, event],
          streamedAssistantDraft,
          error:
            event.event_type === "agent.turn.failed"
              ? new Error(
                  typeof (event.payload.error as { message?: unknown } | undefined)?.message === "string"
                    ? ((event.payload.error as { message: string }).message)
                    : "The analyst failed to complete the turn.",
                )
              : current.error,
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
        void refreshSessionState();
      }

      if (terminalEventTypes.has(event.event_type)) {
        isClosed = true;
        unsubscribe();
      }
    });

    return () => {
      isClosed = true;
      unsubscribe();
    };
  }, [state.session?.session_id, state.session?.status]);

  async function startSession(inputText: string) {
    setState((current) => ({
      ...current,
      isConnecting: true,
      error: null,
    }));
    try {
      const session = await createChatSession({ inputText });
      const items = await getSessionItems(session.session_id);
      setState({
        session,
        items,
        events: [],
        streamedAssistantDraft: {
          turnId: null,
          text: "",
        },
        isConnecting: false,
        isSending: false,
        approvalDecisionById: {},
        error: null,
      });
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
        streamedAssistantDraft: {
          turnId: null,
          text: "",
        },
        isSending: false,
        error: null,
      }));
      return session;
    } catch (error) {
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
    setState((current) => ({
      ...current,
      approvalDecisionById: {
        ...current.approvalDecisionById,
        [approvalId]: true,
      },
      error: null,
    }));
    try {
      const session = await decideSessionApproval(approvalId, { approved });
      const items = await getSessionItems(session.session_id);
      setState((current) => {
        const nextDecisionState = { ...current.approvalDecisionById };
        delete nextDecisionState[approvalId];
        return {
          ...current,
          session,
          items,
          approvalDecisionById: nextDecisionState,
          error:
            session.status === "failed"
              ? new Error(session.error_message ?? "The analyst failed to complete the turn.")
              : null,
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
