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
import type { CurrentUser, UserRole } from "@/shared/auth/types";

export type SignupInput = {
  name: string;
  email: string;
  companyName: string;
  role: UserRole;
};

export type AppDataProvider = {
  getCurrentUser(): CurrentUser | null;
  subscribeCurrentUser(listener: () => void): () => void;
  signIn(user: CurrentUser): void;
  signOut(): void;
  signup(input: SignupInput): Promise<CurrentUser>;
  getOnboardingRegistry(): Promise<Registry>;
  getOnboardingProgress(profileId: string): Promise<OnboardingProgress | null>;
  listOnboardingResponses(profileId: string): Promise<OnboardingResponse[]>;
  submitOnboardingResponse(profileId: string, body: OnboardingResponseSubmit): Promise<void>;
  upsertClientContact(
    profileId: string,
    body: Omit<ClientContact, "extension_id" | "profile_id" | "created_at" | "updated_at"> & { status?: string },
  ): Promise<ClientContact>;
  getDashboardData(): Promise<CompanyProfileResponse>;
  listProducts(profileId: string): Promise<unknown[]>;
  createProduct(profileId: string, body: unknown): Promise<unknown>;
  updateProduct(productId: string, body: unknown): Promise<unknown>;
  deleteProduct(productId: string): Promise<void>;
  getExhaustiveView(profileId: string): Promise<SalesbookExhaustiveView>;
  listDeals(profileId: string): Promise<PipelineDeal[]>;
  createDeal(profileId: string, body: PipelineDealCreate): Promise<PipelineDeal>;
  updateDeal(dealId: string, body: PipelineDealUpdate): Promise<PipelineDeal>;
  logEngagement(body: EngagementCreate): Promise<EngagementEntry>;
  listEngagements(profileId: string, opts?: { dealId?: string }): Promise<EngagementEntry[]>;
  listTeam(profileId: string): Promise<TeamMember[]>;
  addTeamMember(profileId: string, body: TeamMemberCreate): Promise<TeamMember>;
  removeTeamMember(membershipId: string): Promise<void>;
  addComment(profileId: string, body: SalesbookCommentCreate): Promise<SalesbookComment>;
  listComments(profileId: string, opts?: { status?: string; targetId?: string }): Promise<SalesbookComment[]>;
  reviewComment(commentId: string, body: { approved_by: string; decision: "approved" | "rejected" }): Promise<SalesbookComment>;
  listPins(profileId: string): Promise<SalesbookPin[]>;
  pinEntry(profileId: string, body: { target_type: string; target_id: string; pinned_by: string }): Promise<SalesbookPin>;
  unpinEntry(profileId: string, target_type: string, target_id: string): Promise<void>;
  createChatSession(input: CreateChatSessionInput): Promise<SessionSummary>;
  listChatSessions(): Promise<SessionSummary[]>;
  getChatSession(sessionId: string): Promise<SessionSummary>;
  sendChatMessage(sessionId: string, inputText: string): Promise<SessionSummary>;
  getChatSessionItems(sessionId: string): Promise<SessionItem[]>;
  getChatSessionEvents(sessionId: string): Promise<SessionEvent[]>;
  subscribeToChatSessionEvents(sessionId: string, afterSequence: number, onEvent: (event: SessionEvent) => void): () => void;
  cancelChatSession(sessionId: string): Promise<SessionSummary>;
  decideChatApproval(approvalId: string, input: ApprovalDecisionInput): Promise<ApprovalDecision>;
};