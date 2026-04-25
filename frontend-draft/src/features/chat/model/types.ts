export type ApiEnvelope<T> = {
  ok: true;
  data: T;
};

export type SessionSummary = {
  session_id: string;
  status: string;
  profile_name: string;
  actor_id: string | null;
  user_id: string | null;
  org_id: string | null;
  request_id: string | null;
  trace_id: string | null;
  latest_item_id: string | null;
  latest_run_id: string | null;
  summary_task_id: string | null;
  summary_status: string | null;
  last_summarized_item_sequence: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  error_code: string | null;
  error_category: string | null;
  error_message: string | null;
};

export type SessionItem = {
  item_id: string;
  sequence_no: number;
  item_type: string;
  actor_id: string | null;
  run_id: string | null;
  turn_id: string | null;
  tool_call_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type SessionEvent = {
  event_id: string;
  sequence_no: number;
  event_type: string;
  severity: string;
  code: string | null;
  run_id: string | null;
  turn_id: string | null;
  tool_call_id: string | null;
  request_id: string | null;
  trace_id: string | null;
  actor_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type CreateChatSessionInput = {
  inputText: string;
  userId?: string;
  orgId?: string;
};

export type StreamedAssistantDraft = {
  turnId: string | null;
  text: string;
};

export type ApprovalDecisionInput = {
  approved: boolean;
};

export type ApprovalDecision = {
  approval_id: string;
  approved: boolean;
  run_id: string;
  turn_id: string;
  tool_call_id: string;
  status: string;
};
