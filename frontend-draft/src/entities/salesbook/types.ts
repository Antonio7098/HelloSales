/**
 * Salesbook TypeScript types — mirror of backend Pydantic views.
 * /Oliviercontribution. Keep in sync with
 * backend/src/hello_sales_backend/modules/salesbook/use_cases/views.py
 */

export type RegistryQuestion = {
  phase: number;
  n: number;
  section: string | null;
  subsection?: string | null;
  question: string | null;
  answer_type: string | null;
  example?: string | null;
  key: string;
};

export type Registry = Record<string, RegistryQuestion>;

export type ClientContact = {
  extension_id: string;
  profile_id: string;
  primary_email: string;
  contact_name: string;
  contact_role: string | null;
  phone: string | null;
  company_size: string | null;
  geography: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type OnboardingProgress = {
  progress_id: string;
  profile_id: string;
  current_phase: number;
  phase1_pct: number | string;
  phase2_pct: number | string;
  phase3_pct: number | string;
  phase1_completed_at: string | null;
  phase2_completed_at: string | null;
  phase3_completed_at: string | null;
  total_completion_pct: number | string;
  updated_at: string;
};

export type OnboardingResponse = {
  response_id: string;
  profile_id: string;
  phase: number;
  question_key: string;
  question_text: string | null;
  response_value: string | null;
  response_type: string | null;
  answered_at: string | null;
  updated_at: string;
};

export type OnboardingResponseSubmit = {
  phase: number;
  question_key: string;
  response_value?: string | null;
  response_type?: string | null;
  question_text?: string | null;
};

export type PipelineDeal = {
  deal_id: string;
  profile_id: string;
  stage: string;
  lead_source: string | null;
  lead_score: number;
  assigned_agent: string | null;
  deal_value: number | string;
  deal_probability: number | string;
  next_action: string | null;
  next_action_date: string | null;
  stage_entered_at: string;
  created_at: string;
  closed_at: string | null;
  close_reason: string | null;
};

export type PipelineDealCreate = {
  stage?: string;
  lead_source?: string | null;
  lead_score?: number;
  assigned_agent?: string | null;
  deal_value?: number | string;
  deal_probability?: number | string;
  next_action?: string | null;
  next_action_date?: string | null;
};

export type PipelineDealUpdate = Partial<PipelineDealCreate> & {
  close_reason?: string | null;
};

export type EngagementEntry = {
  log_id: string;
  profile_id: string;
  deal_id: string | null;
  action_type: string;
  action_detail: string | null;
  action_reason: string | null;
  action_result: string | null;
  next_step: string | null;
  channel: string | null;
  agent_id: string | null;
  process_version: string | null;
  timestamp: string;
};

export type EngagementCreate = {
  profile_id: string;
  deal_id?: string | null;
  action_type: string;
  action_detail?: string | null;
  action_reason?: string | null;
  action_result?: string | null;
  next_step?: string | null;
  channel?: string | null;
  agent_id?: string | null;
  process_version?: string | null;
};

export type TeamMember = {
  membership_id: string;
  profile_id: string;
  user_email: string;
  role_level: string;
  can_invite: boolean;
  can_export: boolean;
  can_edit_onboarding: boolean;
  created_at: string;
};

export type TeamMemberCreate = {
  user_email: string;
  role_level?: string;
  can_invite?: boolean;
  can_export?: boolean;
  can_edit_onboarding?: boolean;
};

export type SalesbookComment = {
  comment_id: string;
  profile_id: string;
  target_type: string;
  target_id: string;
  author_email: string;
  body: string;
  status: "pending" | "approved" | "rejected";
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SalesbookCommentCreate = {
  target_type?: string;
  target_id: string;
  author_email: string;
  body: string;
};

export type SalesbookPin = {
  pin_id: string;
  profile_id: string;
  target_type: string;
  target_id: string;
  pinned_by: string;
  pinned_at: string;
};

export type SalesbookExhaustiveOnboardingEntry = {
  phase: number;
  section: string | null;
  question_key: string;
  question_text: string | null;
  response_value: string | null;
  response_type: string | null;
  answered_at: string | null;
};

export type SalesbookExhaustiveProductEntry = {
  product_id: string;
  product_name: string;
  product_description: string | null;
  target_customer: string | null;
  primary_use_case: string | null;
  pricing_model: string | null;
  list_price: string | null;
  sales_cycle: string | null;
  deal_size: string | null;
  revenue_share: string | null;
  is_primary: boolean;
};

export type SalesbookExhaustiveView = {
  profile_id: string;
  contact: ClientContact | null;
  progress: OnboardingProgress | null;
  onboarding: SalesbookExhaustiveOnboardingEntry[];
  products: SalesbookExhaustiveProductEntry[];
  pipeline: PipelineDeal[];
  engagement: EngagementEntry[];
  team: TeamMember[];
  comments: SalesbookComment[];
  pinned: SalesbookPin[];
};
