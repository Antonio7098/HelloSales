import { getSalesbookApi } from "./salesbook-api";

describe("salesbook api client", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("getOnboardingRegistry hits fastapi route and unwraps questions", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, data: { questions: { q1: { key: "q1", phase: 1 } } } }),
    });

    const api = getSalesbookApi();
    const result = await api.getOnboardingRegistry(1);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/salesbook/onboarding/registry?phase=1",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(result).toEqual({ q1: { key: "q1", phase: 1 } });
  });

  test("upsertClientContact sends PUT body to fastapi route", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        ok: true,
        data: { extension_id: "ext-1", profile_id: "profile-1", primary_email: "owner@example.com" },
      }),
    });

    const api = getSalesbookApi();
    await api.upsertClientContact("profile-1", {
      primary_email: "owner@example.com",
      contact_name: "Owner",
      contact_role: "Founder/VP",
      phone: null,
      company_size: null,
      geography: null,
      status: "active",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/salesbook/clients/profile-1/contact",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          primary_email: "owner@example.com",
          contact_name: "Owner",
          contact_role: "Founder/VP",
          phone: null,
          company_size: null,
          geography: null,
          status: "active",
        }),
      }),
    );
  });

  test("throws the backend error message on failed envelopes", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      json: async () => ({ error: { message: "nope" } }),
    });

    const api = getSalesbookApi();

    await expect(api.getClientContact("profile-1")).rejects.toThrow("nope");
  });
});
