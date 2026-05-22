/**
 * Salesbook API client. /Oliviercontribution.
 *
 * Two implementations behind a single interface:
 *   - FastAPI mode (VITE_USE_SHEETS=false): hits /api/salesbook/* on a backend
 *     deployed somewhere (local, AWS-future).
 *   - Sheets mode  (VITE_USE_SHEETS=true):  POSTs to a Google Apps Script Web
 *     App URL with {action, payload}. The Apps Script (built in 7.1) routes
 *     into the appropriate Google Sheet tab.
 *
 * For the Vercel demo we ship in Sheets mode. The Apps Script and the actual
 * Google Sheet are the demo's data plane. localStorage caches recent reads so
 * the UI feels instant.
 */

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

export type SalesbookApi = {
  getOnboardingRegistry(phase?: number): Promise<Registry>;
  getOnboardingProgress(profileId: string): Promise<OnboardingProgress>;
  listResponses(profileId: string, phase?: number): Promise<OnboardingResponse[]>;
  submitResponse(profileId: string, body: OnboardingResponseSubmit): Promise<OnboardingResponse>;
  submitBatch(profileId: string, body: { phase: number; responses: OnboardingResponseSubmit[] }): Promise<OnboardingResponse[]>;
  getExhaustiveView(profileId: string): Promise<SalesbookExhaustiveView>;
  getClientContact(profileId: string): Promise<ClientContact | null>;
  upsertClientContact(profileId: string, body: Omit<ClientContact, "extension_id" | "profile_id" | "created_at" | "updated_at"> & { status?: string }): Promise<ClientContact>;
  listDeals(profileId: string): Promise<PipelineDeal[]>;
  createDeal(profileId: string, body: PipelineDealCreate): Promise<PipelineDeal>;
  updateDeal(dealId: string, body: PipelineDealUpdate): Promise<PipelineDeal>;
  logEngagement(body: EngagementCreate): Promise<EngagementEntry>;
  listEngagements(profileId: string, opts?: { dealId?: string; limit?: number }): Promise<EngagementEntry[]>;
  listAllEngagements(limit?: number): Promise<EngagementEntry[]>;
  listTeam(profileId: string): Promise<TeamMember[]>;
  addTeamMember(profileId: string, body: TeamMemberCreate): Promise<TeamMember>;
  removeTeamMember(membershipId: string): Promise<void>;
  // Moderation
  addComment(profileId: string, body: SalesbookCommentCreate): Promise<SalesbookComment>;
  listComments(profileId: string, opts?: { status?: string; targetId?: string }): Promise<SalesbookComment[]>;
  reviewComment(commentId: string, body: { approved_by: string; decision: "approved" | "rejected" }): Promise<SalesbookComment>;
  listPins(profileId: string): Promise<SalesbookPin[]>;
  pinEntry(profileId: string, body: { target_type: string; target_id: string; pinned_by: string }): Promise<SalesbookPin>;
  unpinEntry(profileId: string, target_type: string, target_id: string): Promise<void>;
  // Demo signup (Sheets mode only)
  signup?(body: { name: string; email: string; companyName: string; role: "admin" | "rep" }): Promise<{ profileId: string }>;
};

const USE_SHEETS = import.meta.env.VITE_USE_SHEETS === "true";
const API_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const SHEETS_URL = (import.meta.env.VITE_SHEETS_WEBHOOK_URL ?? "").replace(/\/$/, "");

// ─── FastAPI implementation ────────────────────────────────────────────────

async function fastapi<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}/api/salesbook${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  const json = await r.json();
  if (!r.ok || json.ok === false) {
    throw new Error(json?.error?.message ?? `Request failed: ${r.status}`);
  }
  return json.data as T;
}

const fastapiApi: SalesbookApi = {
  async getOnboardingRegistry(phase) {
    const q = phase ? `?phase=${phase}` : "";
    const data = await fastapi<{ questions: Registry }>(`/onboarding/registry${q}`);
    return data.questions;
  },
  getOnboardingProgress: (pid) => fastapi(`/clients/${pid}/onboarding/progress`),
  listResponses: (pid, phase) =>
    fastapi(`/clients/${pid}/onboarding/responses${phase ? `?phase=${phase}` : ""}`),
  submitResponse: (pid, body) =>
    fastapi(`/clients/${pid}/onboarding/responses`, { method: "POST", body: JSON.stringify(body) }),
  submitBatch: (pid, body) =>
    fastapi(`/clients/${pid}/onboarding/batch`, { method: "POST", body: JSON.stringify(body) }),
  getExhaustiveView: (pid) => fastapi(`/clients/${pid}/salesbook`),
  getClientContact: (pid) => fastapi(`/clients/${pid}/contact`),
  upsertClientContact: (pid, body) =>
    fastapi(`/clients/${pid}/contact`, { method: "PUT", body: JSON.stringify(body) }),
  listDeals: (pid) => fastapi(`/clients/${pid}/pipeline`),
  createDeal: (pid, body) =>
    fastapi(`/clients/${pid}/pipeline`, { method: "POST", body: JSON.stringify(body) }),
  updateDeal: (deal_id, body) =>
    fastapi(`/pipeline/${deal_id}`, { method: "PATCH", body: JSON.stringify(body) }),
  logEngagement: (body) =>
    fastapi(`/engagement-log`, { method: "POST", body: JSON.stringify(body) }),
  listEngagements: (pid, opts) => {
    const params = new URLSearchParams();
    if (opts?.dealId) params.set("deal_id", opts.dealId);
    if (opts?.limit) params.set("limit", String(opts.limit));
    const q = params.toString();
    return fastapi(`/clients/${pid}/engagement-log${q ? `?${q}` : ""}`);
  },
  listAllEngagements: (limit) =>
    fastapi(`/engagement-log/all${limit ? `?limit=${limit}` : ""}`),
  listTeam: (pid) => fastapi(`/clients/${pid}/team`),
  addTeamMember: (pid, body) =>
    fastapi(`/clients/${pid}/team`, { method: "POST", body: JSON.stringify(body) }),
  async removeTeamMember(mid) {
    await fastapi(`/team/${mid}`, { method: "DELETE" });
  },
  addComment: (pid, body) =>
    fastapi(`/clients/${pid}/comments`, { method: "POST", body: JSON.stringify(body) }),
  listComments: (pid, opts) => {
    const params = new URLSearchParams();
    if (opts?.status) params.set("status", opts.status);
    if (opts?.targetId) params.set("target_id", opts.targetId);
    const q = params.toString();
    return fastapi(`/clients/${pid}/comments${q ? `?${q}` : ""}`);
  },
  reviewComment: (cid, body) =>
    fastapi(`/comments/${cid}/review`, { method: "PATCH", body: JSON.stringify(body) }),
  listPins: (pid) => fastapi(`/clients/${pid}/pins`),
  pinEntry: (pid, body) =>
    fastapi(`/clients/${pid}/pins`, { method: "POST", body: JSON.stringify(body) }),
  async unpinEntry(pid, target_type, target_id) {
    const params = new URLSearchParams({ target_type, target_id });
    await fastapi(`/clients/${pid}/pins?${params}`, { method: "DELETE" });
  },
};

// ─── Sheets (Apps Script) implementation ──────────────────────────────────

async function sheetsCall<T>(action: string, payload: Record<string, unknown>): Promise<T> {
  if (!SHEETS_URL) {
    throw new Error("VITE_SHEETS_WEBHOOK_URL not configured. Set it in your Vercel env.");
  }
  const r = await fetch(SHEETS_URL, {
    method: "POST",
    headers: { "Content-Type": "text/plain;charset=utf-8" }, // avoid CORS preflight
    body: JSON.stringify({ action, payload }),
    redirect: "follow",
  });
  const json = await r.json();
  if (!json.ok) throw new Error(json?.error ?? `Sheets call failed: ${action}`);
  return json.data as T;
}

const sheetsApi: SalesbookApi = {
  async getOnboardingRegistry(_phase) {
    // Static registry shipped with the frontend (copied from backend at build time)
    const r = await fetch("/onboarding-registry.json");
    if (!r.ok) {
      throw new Error("onboarding-registry.json missing in public/. Run npm run copy-registry.");
    }
    const arr = (await r.json()) as Array<{ key: string } & Record<string, unknown>>;
    const out: Registry = {};
    for (const q of arr) out[q.key] = q as never;
    return out;
  },
  getOnboardingProgress: (pid) => sheetsCall("get_onboarding_progress", { profileId: pid }),
  listResponses: (pid, phase) =>
    sheetsCall("get_onboarding_responses", { profileId: pid, phase }),
  submitResponse: (pid, body) =>
    sheetsCall("submit_onboarding_response", { profileId: pid, ...body }),
  submitBatch: (pid, body) =>
    sheetsCall("submit_onboarding_batch", { profileId: pid, ...body }),
  getExhaustiveView: (pid) => sheetsCall("get_salesbook_exhaustive", { profileId: pid }),
  getClientContact: (pid) => sheetsCall("get_client_contact", { profileId: pid }),
  upsertClientContact: (pid, body) =>
    sheetsCall("upsert_client_contact", { profileId: pid, ...body }),
  listDeals: (pid) => sheetsCall("list_deals", { profileId: pid }),
  createDeal: (pid, body) => sheetsCall("create_deal", { profileId: pid, ...body }),
  updateDeal: (deal_id, body) => sheetsCall("update_deal", { dealId: deal_id, ...body }),
  logEngagement: (body) => sheetsCall("log_engagement", body as Record<string, unknown>),
  listEngagements: (pid, opts) =>
    sheetsCall("list_engagements", { profileId: pid, dealId: opts?.dealId, limit: opts?.limit }),
  listAllEngagements: (limit) => sheetsCall("list_all_engagements", { limit }),
  listTeam: (pid) => sheetsCall("list_team", { profileId: pid }),
  addTeamMember: (pid, body) => sheetsCall("add_team_member", { profileId: pid, ...body }),
  async removeTeamMember(mid) {
    await sheetsCall("remove_team_member", { membershipId: mid });
  },
  addComment: (pid, body) => sheetsCall("add_comment", { profileId: pid, ...body }),
  listComments: (pid, opts) =>
    sheetsCall("list_comments", { profileId: pid, status: opts?.status, targetId: opts?.targetId }),
  reviewComment: (cid, body) => sheetsCall("review_comment", { commentId: cid, ...body }),
  listPins: (pid) => sheetsCall("list_pins", { profileId: pid }),
  pinEntry: (pid, body) => sheetsCall("pin_entry", { profileId: pid, ...body }),
  async unpinEntry(pid, target_type, target_id) {
    await sheetsCall("unpin_entry", { profileId: pid, target_type, target_id });
  },
  signup: (body) => sheetsCall("signup", body as Record<string, unknown>),
};

let _api: SalesbookApi | null = null;

export function getSalesbookApi(): SalesbookApi {
  if (_api === null) {
    _api = USE_SHEETS ? sheetsApi : fastapiApi;
  }
  return _api;
}

export const isSheetsMode = USE_SHEETS;
