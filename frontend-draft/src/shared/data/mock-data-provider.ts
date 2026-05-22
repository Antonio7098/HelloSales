import type {
  ClientContact,
  EngagementCreate,
  EngagementEntry,
  OnboardingProgress,
  OnboardingResponse,
  OnboardingResponseSubmit,
  PipelineDeal,
  PipelineDealCreate,
  PipelineDealUpdate,
  Registry,
  RegistryQuestion,
  SalesbookComment,
  SalesbookCommentCreate,
  SalesbookExhaustiveView,
  SalesbookPin,
  TeamMember,
  TeamMemberCreate,
} from "@/entities/salesbook/types";
import type { CompanyProfileResponse } from "@/features/dashboard-data/model/types";
import type { ApprovalDecision, ApprovalDecisionInput, CreateChatSessionInput, SessionEvent, SessionItem, SessionSummary } from "@/features/chat/model/types";
import type { CurrentUser } from "@/shared/auth/types";
import type { AppDataProvider, SignupInput } from "@/shared/data/provider";

const USER_KEY = "hs:user";
const RESPONSES_KEY = "hs:mock:onboarding-responses";
const CONTACTS_KEY = "hs:mock:contacts";
const DEALS_KEY = "hs:mock:deals";
const ENGAGEMENTS_KEY = "hs:mock:engagements";
const COMMENTS_KEY = "hs:mock:comments";
const PINS_KEY = "hs:mock:pins";
const TEAM_KEY = "hs:mock:team";
const SESSIONS_KEY = "hs:mock:sessions";
const USER_EVENT = "hs:user-changed";

function isBrowser() {
  return typeof window !== "undefined";
}

function readJson<T>(key: string, fallback: T): T {
  if (!isBrowser()) return fallback;
  const raw = window.localStorage.getItem(key);
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson<T>(key: string, value: T) {
  if (!isBrowser()) return;
  window.localStorage.setItem(key, JSON.stringify(value));
}

function buildProfileId(email: string): string {
  return `demo-${email.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`;
}

function loadRegistry(): Promise<Registry> {
  return fetch("/onboarding-registry.json").then(async (response) => {
    if (!response.ok) throw new Error("onboarding-registry.json missing in public/.");
    const questions = (await response.json()) as Array<{ key: string } & Record<string, unknown>>;
    const registry: Registry = {};
    for (const question of questions) {
      registry[question.key] = question as Registry[string];
    }
    return registry;
  });
}

function loadAllResponses(): Record<string, OnboardingResponse[]> {
  return readJson(RESPONSES_KEY, {} as Record<string, OnboardingResponse[]>);
}

function saveAllResponses(value: Record<string, OnboardingResponse[]>) {
  writeJson(RESPONSES_KEY, value);
}

function computeProgress(profileId: string, registry: Registry, responses: OnboardingResponse[]): OnboardingProgress {
  const now = new Date().toISOString();
  const questions = Object.values(registry) as RegistryQuestion[];
  const answered = new Set(
    responses.filter((response) => (response.response_value ?? "").trim() !== "").map((response) => response.question_key),
  );
  const phaseStats = [1, 2, 3].map((phase) => {
    const phaseQuestions = questions.filter((question: RegistryQuestion) => question.phase === phase);
    const phaseAnswered = phaseQuestions.filter((question: RegistryQuestion) => answered.has(question.key)).length;
    const pct = phaseQuestions.length === 0 ? 0 : (phaseAnswered / phaseQuestions.length) * 100;
    return { pct, completedAt: phaseQuestions.length > 0 && phaseAnswered === phaseQuestions.length ? now : null };
  });
  const totalCompletionPct = questions.length === 0 ? 0 : (answered.size / questions.length) * 100;
  const currentPhase = phaseStats.findIndex((phase) => phase.pct < 100) + 1 || 3;
  return {
    progress_id: `mock-progress-${profileId}`,
    profile_id: profileId,
    current_phase: currentPhase,
    phase1_pct: phaseStats[0]?.pct ?? 0,
    phase2_pct: phaseStats[1]?.pct ?? 0,
    phase3_pct: phaseStats[2]?.pct ?? 0,
    phase1_completed_at: phaseStats[0]?.completedAt ?? null,
    phase2_completed_at: phaseStats[1]?.completedAt ?? null,
    phase3_completed_at: phaseStats[2]?.completedAt ?? null,
    total_completion_pct: totalCompletionPct,
    updated_at: now,
  };
}

// ── Seed data ────────────────────────────────────────────────────────────────

const MOCK_COMPANY_PROFILE: CompanyProfileResponse = {
  profile_id: "mock-profile",
  company_name: "Northline Systems",
  industry: "SaaS",
  target_customer: "Mid-market B2B",
  pricing_model: "Per-seat",
  sales_team_size: 12,
  crm_tool: "Salesforce",
  average_deal_size: "$28k ARR",
  average_sales_cycle: "45 days",
  primary_sales_constraint: "Lead follow-up speed",
  quarterly_sales_focus: "Expand mid-market accounts",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const MOCK_DEALS: PipelineDeal[] = [
  {
    deal_id: "deal-001", profile_id: "mock-profile", stage: "new", lead_source: "Inbound", lead_score: 82,
    assigned_agent: null, deal_value: "14k ARR", deal_probability: "20%", next_action: "Initial call",
    next_action_date: null, stage_entered_at: new Date().toISOString(), created_at: new Date().toISOString(),
    closed_at: null, close_reason: null,
  },
  {
    deal_id: "deal-002", profile_id: "mock-profile", stage: "qualified", lead_source: "Outbound", lead_score: 71,
    assigned_agent: null, deal_value: "22k ARR", deal_probability: "40%", next_action: "Demo scheduled",
    next_action_date: null, stage_entered_at: new Date().toISOString(), created_at: new Date().toISOString(),
    closed_at: null, close_reason: null,
  },
  {
    deal_id: "deal-003", profile_id: "mock-profile", stage: "proposal", lead_source: "Inbound", lead_score: 90,
    assigned_agent: null, deal_value: "40k ARR", deal_probability: "60%", next_action: "Proposal review",
    next_action_date: null, stage_entered_at: new Date().toISOString(), created_at: new Date().toISOString(),
    closed_at: null, close_reason: null,
  },
  {
    deal_id: "deal-004", profile_id: "mock-profile", stage: "closed_won", lead_source: "Referral", lead_score: 95,
    assigned_agent: null, deal_value: "55k ARR", deal_probability: "100%", next_action: null,
    next_action_date: null, stage_entered_at: new Date().toISOString(), created_at: new Date().toISOString(),
    closed_at: new Date().toISOString(), close_reason: "Won",
  },
];

const MOCK_PRODUCTS = [
  { product_id: "prod-001", product_name: "Hello Sales Pro", product_description: "Full sales intelligence suite", target_customer: "Mid-market B2B", primary_use_case: "Pipeline management", pricing_model: "Per-seat", list_price: "$99/user/mo", sales_cycle: "30 days", deal_size: "$12k-$60k ARR", revenue_share: "20%", is_primary: true },
  { product_id: "prod-002", product_name: "Hello Sales Starter", product_description: "Essential sales tooling", target_customer: "SMB", primary_use_case: "Lead tracking", pricing_model: "Per-seat", list_price: "$29/user/mo", sales_cycle: "14 days", deal_size: "$1k-$10k ARR", revenue_share: "30%", is_primary: false },
];

const MOCK_EXHAUSTIVE_VIEW = (profileId: string): SalesbookExhaustiveView => ({
  profile_id: profileId,
  contact: null,
  progress: null,
  onboarding: [],
  products: MOCK_PRODUCTS as SalesbookExhaustiveView["products"],
  pipeline: MOCK_DEALS,
  engagement: [],
  team: [],
  comments: [],
  pinned: [],
});

const MOCK_TEAM: TeamMember[] = [
  {
    membership_id: "member-001", profile_id: "mock-profile", user_email: "alice@acme.com",
    role_level: "admin", can_invite: true, can_export: true, can_edit_onboarding: true, created_at: new Date().toISOString(),
  },
  {
    membership_id: "member-002", profile_id: "mock-profile", user_email: "bob@acme.com",
    role_level: "rep", can_invite: false, can_export: true, can_edit_onboarding: false, created_at: new Date().toISOString(),
  },
];

const MOCK_COMMENTS: SalesbookComment[] = [
  {
    comment_id: "comment-001", profile_id: "mock-profile", target_type: "deal", target_id: "deal-001",
    author_email: "alice@acme.com", body: "Strong fit for the enterprise tier.", status: "approved",
    approved_by: "alice@acme.com", approved_at: new Date().toISOString(), created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  },
];

const MOCK_PINS: SalesbookPin[] = [
  {
    pin_id: "pin-001", profile_id: "mock-profile", target_type: "deal", target_id: "deal-003",
    pinned_by: "alice@acme.com", pinned_at: new Date().toISOString(),
  },
];

// ── Counters ──────────────────────────────────────────────────────────────

let dealCounter = 100;
let engagementCounter = 1;
let membershipCounter = 10;
let commentCounter = 10;
let pinCounter = 10;
let sessionCounter = 10;
let eventSequenceCounter = 1;

export const mockDataProvider: AppDataProvider = {
  getCurrentUser() {
    return readJson<CurrentUser | null>(USER_KEY, null);
  },
  subscribeCurrentUser(listener) {
    if (!isBrowser()) return () => {};
    window.addEventListener(USER_EVENT, listener);
    window.addEventListener("storage", listener);
    return () => {
      window.removeEventListener(USER_EVENT, listener);
      window.removeEventListener("storage", listener);
    };
  },
  signIn(user) {
    writeJson(USER_KEY, user);
    if (isBrowser()) window.dispatchEvent(new CustomEvent(USER_EVENT));
  },
  signOut() {
    if (!isBrowser()) return;
    window.localStorage.removeItem(USER_KEY);
    window.dispatchEvent(new CustomEvent(USER_EVENT));
  },
  async signup(input: SignupInput) {
    const user: CurrentUser = {
      profileId: buildProfileId(input.email),
      email: input.email,
      name: input.name,
      companyName: input.companyName,
      role: input.role,
      signedUpAt: new Date().toISOString(),
    };
    this.signIn(user);
    return user;
  },
  getOnboardingRegistry() {
    return loadRegistry();
  },
  async getOnboardingProgress(profileId) {
    const registry = await loadRegistry();
    const responses = loadAllResponses()[profileId] ?? [];
    return computeProgress(profileId, registry, responses);
  },
  async listOnboardingResponses(profileId) {
    return loadAllResponses()[profileId] ?? [];
  },
  async submitOnboardingResponse(profileId, body) {
    const allResponses = loadAllResponses();
    const current = allResponses[profileId] ?? [];
    const now = new Date().toISOString();
    const next: OnboardingResponse = {
      response_id: `${profileId}:${body.question_key}`,
      profile_id: profileId,
      phase: body.phase,
      question_key: body.question_key,
      question_text: body.question_text ?? null,
      response_value: body.response_value ?? null,
      response_type: body.response_type ?? null,
      answered_at: body.response_value ? now : null,
      updated_at: now,
    };
    const filtered = current.filter((response) => response.question_key !== body.question_key);
    allResponses[profileId] = [...filtered, next];
    saveAllResponses(allResponses);
  },
  async upsertClientContact(profileId, body) {
    const contacts = readJson<Record<string, ClientContact>>(CONTACTS_KEY, {});
    const now = new Date().toISOString();
    const existing = contacts[profileId];
    const next: ClientContact = {
      extension_id: existing?.extension_id ?? `mock-contact-${profileId}`,
      profile_id: profileId,
      primary_email: body.primary_email,
      contact_name: body.contact_name,
      contact_role: body.contact_role ?? null,
      phone: body.phone ?? null,
      company_size: body.company_size ?? null,
      geography: body.geography ?? null,
      status: body.status ?? "active",
      created_at: existing?.created_at ?? now,
      updated_at: now,
    };
    contacts[profileId] = next;
    writeJson(CONTACTS_KEY, contacts);
    return next;
  },
  async getDashboardData() {
    return MOCK_COMPANY_PROFILE;
  },
  async listProducts(profileId) {
    return MOCK_PRODUCTS;
  },
  async createProduct(profileId, body) {
    const product = { product_id: `prod-${++dealCounter}`, ...(body as Record<string, unknown>), profile_id: profileId };
    return product;
  },
  async updateProduct(productId, body) {
    return { product_id: productId, ...(body as Record<string, unknown>) };
  },
  async deleteProduct(_productId) {
    return;
  },
  async getExhaustiveView(profileId) {
    return MOCK_EXHAUSTIVE_VIEW(profileId);
  },
  async listDeals(profileId) {
    const allDeals = readJson<Record<string, PipelineDeal[]>>(DEALS_KEY, {});
    return allDeals[profileId] ?? MOCK_DEALS;
  },
  async createDeal(profileId, body) {
    const allDeals = readJson<Record<string, PipelineDeal[]>>(DEALS_KEY, {});
    const now = new Date().toISOString();
    const deal: PipelineDeal = {
      deal_id: `mock-deal-${++dealCounter}`,
      profile_id: profileId,
      stage: body.stage ?? "new",
      lead_source: body.lead_source ?? null,
      lead_score: body.lead_score ?? 50,
      assigned_agent: body.assigned_agent ?? null,
      deal_value: body.deal_value ?? "0",
      deal_probability: body.deal_probability ?? "0%",
      next_action: body.next_action ?? null,
      next_action_date: body.next_action_date ?? null,
      stage_entered_at: now,
      created_at: now,
      closed_at: null,
      close_reason: null,
    };
    const existing = allDeals[profileId] ?? [];
    allDeals[profileId] = [...existing, deal];
    writeJson(DEALS_KEY, allDeals);
    return deal;
  },
  async updateDeal(dealId, body) {
    const allDeals = readJson<Record<string, PipelineDeal[]>>(DEALS_KEY, {});
    for (const profileId of Object.keys(allDeals)) {
      const idx = allDeals[profileId].findIndex((d) => d.deal_id === dealId);
      if (idx >= 0) {
        const existing = allDeals[profileId][idx];
        allDeals[profileId][idx] = {
          ...existing,
          stage: body.stage ?? existing.stage,
          lead_source: body.lead_source ?? existing.lead_source,
          lead_score: body.lead_score ?? existing.lead_score,
          assigned_agent: body.assigned_agent ?? existing.assigned_agent,
          deal_value: body.deal_value ?? existing.deal_value,
          deal_probability: body.deal_probability ?? existing.deal_probability,
          next_action: body.next_action ?? existing.next_action,
          next_action_date: body.next_action_date ?? existing.next_action_date,
          close_reason: body.close_reason ?? existing.close_reason,
        };
        writeJson(DEALS_KEY, allDeals);
        return allDeals[profileId][idx];
      }
    }
    throw new Error(`Deal ${dealId} not found`);
  },
  async logEngagement(body) {
    const allEngagements = readJson<Record<string, EngagementEntry[]>>(ENGAGEMENTS_KEY, {});
    const now = new Date().toISOString();
    const entry: EngagementEntry = {
      log_id: `mock-engagement-${++engagementCounter}`,
      profile_id: body.profile_id,
      deal_id: body.deal_id ?? null,
      action_type: body.action_type,
      action_detail: body.action_detail ?? null,
      action_reason: body.action_reason ?? null,
      action_result: body.action_result ?? null,
      next_step: body.next_step ?? null,
      channel: body.channel ?? null,
      agent_id: body.agent_id ?? null,
      process_version: body.process_version ?? null,
      timestamp: now,
    };
    const profileEngagements = allEngagements[body.profile_id] ?? [];
    allEngagements[body.profile_id] = [...profileEngagements, entry];
    writeJson(ENGAGEMENTS_KEY, allEngagements);
    return entry;
  },
  async listEngagements(profileId, opts) {
    const allEngagements = readJson<Record<string, EngagementEntry[]>>(ENGAGEMENTS_KEY, {});
    return (allEngagements[profileId] ?? []).filter((e) =>
      opts?.dealId ? e.deal_id === opts.dealId : true,
    );
  },
  async listTeam(profileId) {
    const allTeam = readJson<Record<string, TeamMember[]>>(TEAM_KEY, {});
    return allTeam[profileId] ?? MOCK_TEAM;
  },
  async addTeamMember(profileId, body) {
    const allTeam = readJson<Record<string, TeamMember[]>>(TEAM_KEY, {});
    const member: TeamMember = {
      membership_id: `mock-member-${++membershipCounter}`,
      profile_id: profileId,
      user_email: body.user_email,
      role_level: body.role_level ?? "rep",
      can_invite: body.can_invite ?? false,
      can_export: body.can_export ?? false,
      can_edit_onboarding: body.can_edit_onboarding ?? false,
      created_at: new Date().toISOString(),
    };
    const existing = allTeam[profileId] ?? [];
    allTeam[profileId] = [...existing, member];
    writeJson(TEAM_KEY, allTeam);
    return member;
  },
  async removeTeamMember(membershipId) {
    const allTeam = readJson<Record<string, TeamMember[]>>(TEAM_KEY, {});
    for (const profileId of Object.keys(allTeam)) {
      const filtered = allTeam[profileId].filter((m) => m.membership_id !== membershipId);
      if (filtered.length !== allTeam[profileId].length) {
        allTeam[profileId] = filtered;
        writeJson(TEAM_KEY, allTeam);
        return;
      }
    }
  },
  async addComment(profileId, body) {
    const allComments = readJson<Record<string, SalesbookComment[]>>(COMMENTS_KEY, {});
    const now = new Date().toISOString();
    const comment: SalesbookComment = {
      comment_id: `mock-comment-${++commentCounter}`,
      profile_id: profileId,
      target_type: body.target_type ?? "deal",
      target_id: body.target_id,
      author_email: body.author_email,
      body: body.body,
      status: "pending",
      approved_by: null,
      approved_at: null,
      created_at: now,
      updated_at: now,
    };
    const existing = allComments[profileId] ?? [];
    allComments[profileId] = [...existing, comment];
    writeJson(COMMENTS_KEY, allComments);
    return comment;
  },
  async listComments(profileId, opts) {
    const allComments = readJson<Record<string, SalesbookComment[]>>(COMMENTS_KEY, {});
    return (allComments[profileId] ?? []).filter((c) =>
      opts?.status ? c.status === opts.status : opts?.targetId ? c.target_id === opts.targetId : true,
    );
  },
  async reviewComment(commentId, body) {
    const allComments = readJson<Record<string, SalesbookComment[]>>(COMMENTS_KEY, {});
    for (const profileId of Object.keys(allComments)) {
      const idx = allComments[profileId].findIndex((c) => c.comment_id === commentId);
      if (idx >= 0) {
        allComments[profileId][idx] = {
          ...allComments[profileId][idx],
          status: body.decision,
          approved_by: body.approved_by,
          approved_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        writeJson(COMMENTS_KEY, allComments);
        return allComments[profileId][idx];
      }
    }
    throw new Error(`Comment ${commentId} not found`);
  },
  async listPins(profileId) {
    const allPins = readJson<Record<string, SalesbookPin[]>>(PINS_KEY, {});
    return allPins[profileId] ?? MOCK_PINS;
  },
  async pinEntry(profileId, body) {
    const allPins = readJson<Record<string, SalesbookPin[]>>(PINS_KEY, {});
    const pin: SalesbookPin = {
      pin_id: `mock-pin-${++pinCounter}`,
      profile_id: profileId,
      target_type: body.target_type,
      target_id: body.target_id,
      pinned_by: body.pinned_by,
      pinned_at: new Date().toISOString(),
    };
    const existing = allPins[profileId] ?? [];
    allPins[profileId] = [...existing, pin];
    writeJson(PINS_KEY, allPins);
    return pin;
  },
  async unpinEntry(profileId, target_type, target_id) {
    const allPins = readJson<Record<string, SalesbookPin[]>>(PINS_KEY, {});
    if (allPins[profileId]) {
      allPins[profileId] = allPins[profileId].filter(
        (p) => !(p.target_type === target_type && p.target_id === target_id),
      );
      writeJson(PINS_KEY, allPins);
    }
  },

  // ── Chat ────────────────────────────────────────────────────────────────

  async createChatSession(input) {
    const sessions = readJson<SessionSummary[]>(SESSIONS_KEY, []);
    const now = new Date().toISOString();
    const session: SessionSummary = {
      session_id: `mock-session-${++sessionCounter}`,
      status: "active",
      profile_name: "generic",
      actor_id: null,
      user_id: input.userId ?? null,
      org_id: input.orgId ?? null,
      request_id: null,
      trace_id: null,
      latest_item_id: null,
      latest_run_id: null,
      summary_task_id: null,
      summary_status: null,
      last_summarized_item_sequence: 0,
      created_at: now,
      updated_at: now,
      completed_at: null,
      error_code: null,
      error_category: null,
      error_message: null,
    };
    sessions.push(session);
    writeJson(SESSIONS_KEY, sessions);
    return session;
  },
  async listChatSessions() {
    return readJson<SessionSummary[]>(SESSIONS_KEY, []);
  },
  async getChatSession(sessionId) {
    const sessions = readJson<SessionSummary[]>(SESSIONS_KEY, []);
    const found = sessions.find((s) => s.session_id === sessionId);
    if (!found) throw new Error(`Session ${sessionId} not found`);
    return found;
  },
  async sendChatMessage(sessionId, inputText) {
    const sessions = readJson<SessionSummary[]>(SESSIONS_KEY, []);
    const idx = sessions.findIndex((s) => s.session_id === sessionId);
    if (idx < 0) throw new Error(`Session ${sessionId} not found`);
    sessions[idx] = { ...sessions[idx], updated_at: new Date().toISOString() };
    writeJson(SESSIONS_KEY, sessions);
    return sessions[idx];
  },
  async getChatSessionItems(sessionId) {
    return readJson<SessionItem[]>(`hs:mock:session-items-${sessionId}`, []);
  },
  async getChatSessionEvents(sessionId) {
    return readJson<SessionEvent[]>(`hs:mock:session-events-${sessionId}`, []);
  },
  subscribeToChatSessionEvents(_sessionId, _afterSequence, onEvent) {
    let handle: ReturnType<typeof setInterval>;
    let seq = eventSequenceCounter;
    const mockResponses = [
      "Based on the salesbook data, your top constraint appears to be lead follow-up speed.",
      "I can see you've completed Phase 1 onboarding. Shall I summarize your ICP?",
      "Your pipeline shows 3 active deals worth $76k ARR. Want me to model a outreach sequence?",
    ];
    let responseIndex = 0;
    handle = setInterval(() => {
      const event: SessionEvent = {
        event_id: `mock-event-${seq++}`,
        sequence_no: seq,
        event_type: seq === 1 ? "agent.turn.started" : "agent.response.delta",
        severity: "info",
        code: null,
        run_id: null,
        turn_id: `mock-turn-${seq}`,
        tool_call_id: null,
        request_id: null,
        trace_id: null,
        actor_id: null,
        payload: seq === 1
          ? { turn_id: `mock-turn-${seq}` }
          : { delta: mockResponses[responseIndex++ % mockResponses.length], turn_id: `mock-turn-${seq}` },
        created_at: new Date().toISOString(),
      };
      onEvent(event);
      if (seq > 5) {
        clearInterval(handle);
      }
    }, 500);
    return () => clearInterval(handle);
  },
  async cancelChatSession(sessionId) {
    const sessions = readJson<SessionSummary[]>(SESSIONS_KEY, []);
    const idx = sessions.findIndex((s) => s.session_id === sessionId);
    if (idx >= 0) {
      sessions[idx] = { ...sessions[idx], status: "cancelled", updated_at: new Date().toISOString(), completed_at: new Date().toISOString() };
      writeJson(SESSIONS_KEY, sessions);
      return sessions[idx];
    }
    throw new Error(`Session ${sessionId} not found`);
  },
  async decideChatApproval(approvalId, input) {
    const decision: ApprovalDecision = {
      approval_id: approvalId,
      approved: input.approved,
      run_id: "mock-run",
      turn_id: "mock-turn",
      tool_call_id: "mock-tool",
      status: input.approved ? "approved" : "rejected",
    };
    return decision;
  },
};