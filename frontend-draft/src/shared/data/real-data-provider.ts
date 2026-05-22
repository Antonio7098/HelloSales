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
  SalesbookComment,
  SalesbookCommentCreate,
  SalesbookExhaustiveView,
  SalesbookPin,
  TeamMember,
  TeamMemberCreate,
} from "@/entities/salesbook/types";
import type { CompanyProfileResponse } from "@/features/dashboard-data/model/types";
import type { ApprovalDecision, ApprovalDecisionInput, CreateChatSessionInput, SessionEvent, SessionItem, SessionSummary } from "@/features/chat/model/types";
import { getSalesbookApi, isSheetsMode } from "@/features/salesbook/api/salesbook-api";
import { requestJson } from "@/shared/api/http-client";
import type { CurrentUser } from "@/shared/auth/types";
import type { AppDataProvider, SignupInput } from "@/shared/data/provider";

const USER_KEY = "hs:user";
const USER_EVENT = "hs:user-changed";

function isBrowser() {
  return typeof window !== "undefined";
}

function loadUser(): CurrentUser | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as CurrentUser;
  } catch {
    return null;
  }
}

function saveUser(user: CurrentUser | null) {
  if (!isBrowser()) return;
  if (user === null) {
    window.localStorage.removeItem(USER_KEY);
  } else {
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  window.dispatchEvent(new CustomEvent(USER_EVENT));
}

function buildProfileId(email: string): string {
  return `demo-${email.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`;
}

export const realDataProvider: AppDataProvider = {
  getCurrentUser() {
    return loadUser();
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
    saveUser(user);
  },
  signOut() {
    saveUser(null);
  },
  async signup(input: SignupInput) {
    const api = getSalesbookApi();
    let profileId = buildProfileId(input.email);
    try {
      if (isSheetsMode && api.signup) {
        const result = await api.signup(input);
        if (result?.profileId) profileId = result.profileId;
      } else {
        await api.upsertClientContact(profileId, {
          primary_email: input.email,
          contact_name: input.name,
          contact_role: input.role === "admin" ? "Founder/VP" : "Sales Rep",
          phone: null,
          company_size: null,
          geography: null,
          status: "active",
        });
      }
    } catch (error) {
      console.warn("[signup] backend unreachable, continuing in local-only mode:", error);
    }
    const user: CurrentUser = {
      profileId,
      email: input.email,
      name: input.name,
      companyName: input.companyName,
      role: input.role,
      signedUpAt: new Date().toISOString(),
    };
    saveUser(user);
    return user;
  },
  getOnboardingRegistry(): Promise<Registry> {
    return getSalesbookApi().getOnboardingRegistry();
  },
  async getOnboardingProgress(profileId: string): Promise<OnboardingProgress | null> {
    return getSalesbookApi().getOnboardingProgress(profileId).catch(() => null);
  },
  async listOnboardingResponses(profileId: string): Promise<OnboardingResponse[]> {
    return getSalesbookApi().listResponses(profileId).catch(() => []);
  },
  async submitOnboardingResponse(profileId: string, body: OnboardingResponseSubmit): Promise<void> {
    await getSalesbookApi().submitResponse(profileId, body);
  },
  upsertClientContact(profileId, body) {
    return getSalesbookApi().upsertClientContact(profileId, body);
  },
  async getDashboardData(): Promise<CompanyProfileResponse> {
    const response = await requestJson<{ ok: true; data: CompanyProfileResponse }>({
      path: "/company-profile",
    });
    return response.data;
  },
  async listProducts(profileId: string): Promise<unknown[]> {
    const api = getSalesbookApi();
    return (api as unknown as { listProducts: (pid: string) => Promise<unknown[]> }).listProducts?.(profileId).catch(() => []);
  },
  async createProduct(profileId: string, body: unknown): Promise<unknown> {
    const api = getSalesbookApi();
    return (api as unknown as { createProduct: (pid: string, b: unknown) => Promise<unknown> }).createProduct?.(profileId, body);
  },
  async updateProduct(productId: string, body: unknown): Promise<unknown> {
    const api = getSalesbookApi();
    return (api as unknown as { updateProduct: (id: string, b: unknown) => Promise<unknown> }).updateProduct?.(productId, body);
  },
  async deleteProduct(productId: string): Promise<void> {
    const api = getSalesbookApi() as unknown as { deleteProduct?: (id: string) => Promise<void> };
    await api.deleteProduct?.(productId);
  },
  async getExhaustiveView(profileId: string): Promise<SalesbookExhaustiveView> {
    return getSalesbookApi().getExhaustiveView(profileId);
  },
  async listDeals(profileId: string): Promise<PipelineDeal[]> {
    return getSalesbookApi().listDeals(profileId).catch(() => []);
  },
  async createDeal(profileId: string, body: PipelineDealCreate): Promise<PipelineDeal> {
    return getSalesbookApi().createDeal(profileId, body);
  },
  async updateDeal(dealId: string, body: PipelineDealUpdate): Promise<PipelineDeal> {
    return getSalesbookApi().updateDeal(dealId, body);
  },
  async logEngagement(body: EngagementCreate): Promise<EngagementEntry> {
    return getSalesbookApi().logEngagement(body);
  },
  async listEngagements(profileId: string, opts?: { dealId?: string }): Promise<EngagementEntry[]> {
    return getSalesbookApi().listEngagements(profileId, opts).catch(() => []);
  },
  async listTeam(profileId: string): Promise<TeamMember[]> {
    return getSalesbookApi().listTeam(profileId).catch(() => []);
  },
  async addTeamMember(profileId: string, body: TeamMemberCreate): Promise<TeamMember> {
    return getSalesbookApi().addTeamMember(profileId, body);
  },
  async removeTeamMember(membershipId: string): Promise<void> {
    await getSalesbookApi().removeTeamMember(membershipId);
  },
  async addComment(profileId: string, body: SalesbookCommentCreate): Promise<SalesbookComment> {
    return getSalesbookApi().addComment(profileId, body);
  },
  async listComments(profileId: string, opts?: { status?: string; targetId?: string }): Promise<SalesbookComment[]> {
    return getSalesbookApi().listComments(profileId, opts).catch(() => []);
  },
  async reviewComment(commentId: string, body: { approved_by: string; decision: "approved" | "rejected" }): Promise<SalesbookComment> {
    return getSalesbookApi().reviewComment(commentId, body);
  },
  async listPins(profileId: string): Promise<SalesbookPin[]> {
    return getSalesbookApi().listPins(profileId).catch(() => []);
  },
  async pinEntry(profileId: string, body: { target_type: string; target_id: string; pinned_by: string }): Promise<SalesbookPin> {
    return getSalesbookApi().pinEntry(profileId, body);
  },
  async unpinEntry(profileId: string, target_type: string, target_id: string): Promise<void> {
    await getSalesbookApi().unpinEntry(profileId, target_type, target_id);
  },
  async createChatSession(input: CreateChatSessionInput): Promise<SessionSummary> {
    const response = await requestJson<{ ok: true; data: SessionSummary }>({
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
  },
  async listChatSessions(): Promise<SessionSummary[]> {
    const response = await requestJson<{ ok: true; data: SessionSummary[] }>({
      path: "/sessions",
    });
    return response.data;
  },
  async getChatSession(sessionId: string): Promise<SessionSummary> {
    const response = await requestJson<{ ok: true; data: SessionSummary }>({
      path: `/sessions/${sessionId}`,
    });
    return response.data;
  },
  async sendChatMessage(sessionId: string, inputText: string): Promise<SessionSummary> {
    const response = await requestJson<{ ok: true; data: SessionSummary }>({
      path: `/sessions/${sessionId}/messages`,
      method: "POST",
      body: JSON.stringify({ input_text: inputText }),
    });
    return response.data;
  },
  async getChatSessionItems(sessionId: string): Promise<SessionItem[]> {
    const response = await requestJson<{ ok: true; data: SessionItem[] }>({
      path: `/sessions/${sessionId}/items`,
    });
    return response.data;
  },
  async getChatSessionEvents(sessionId: string): Promise<SessionEvent[]> {
    const response = await requestJson<{ ok: true; data: SessionEvent[] }>({
      path: `/sessions/${sessionId}/events`,
    });
    return response.data;
  },
  subscribeToChatSessionEvents(sessionId: string, afterSequence: number, onEvent: (event: SessionEvent) => void): () => void {
    const url = new URL(`/sessions/${sessionId}/events/stream?after_sequence=${afterSequence}`, window.location.origin);
    const source = new EventSource(url);
    const eventTypes = [
      "agent.tool.queued", "agent.approval.requested", "agent.tool.started", "agent.tool.failed",
      "agent.tool.completed", "agent.response.delta", "agent.turn.started", "agent.turn.awaiting_approval",
      "agent.turn.completed", "agent.turn.cancelled", "agent.turn.failed", "agent.approval.approved",
      "agent.approval.rejected", "agent.run.cancel_requested", "agent.run.cancelled",
    ];
    const listeners = eventTypes.map((eventType) => {
      const listener = (message: MessageEvent<string>) => {
        onEvent(JSON.parse(message.data) as SessionEvent);
      };
      source.addEventListener(eventType, listener);
      return { eventType, listener };
    });
    return () => {
      listeners.forEach(({ eventType, listener }) => source.removeEventListener(eventType, listener));
      source.close();
    };
  },
  async cancelChatSession(sessionId: string): Promise<SessionSummary> {
    const response = await requestJson<{ ok: true; data: SessionSummary }>({
      path: `/sessions/${sessionId}/cancel`,
      method: "POST",
    });
    return response.data;
  },
  async decideChatApproval(approvalId: string, input: ApprovalDecisionInput): Promise<ApprovalDecision> {
    const response = await requestJson<{ ok: true; data: ApprovalDecision }>({
      path: `/sessions/approvals/${approvalId}`,
      method: "POST",
      body: JSON.stringify({ approved: input.approved }),
    });
    return response.data;
  },
};