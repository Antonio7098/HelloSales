import { renderHook, act, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const navigateMock = vi.fn();
const apiMock = {
  getOnboardingRegistry: vi.fn(),
  listResponses: vi.fn(),
  getOnboardingProgress: vi.fn(),
  submitResponse: vi.fn(),
};
const useCurrentUserMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("@/shared/auth/useCurrentUser", () => ({
  useCurrentUser: () => useCurrentUserMock(),
}));

vi.mock("../api/salesbook-api", () => ({
  getSalesbookApi: () => apiMock,
}));

import { useOnboardingFlow } from "./useOnboardingFlow";

function wrapper({ children }: { children: React.ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>;
}

describe("useOnboardingFlow", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    useCurrentUserMock.mockReset();
    Object.values(apiMock).forEach((fn) => fn.mockReset());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("redirects to welcome when no user exists", () => {
    useCurrentUserMock.mockReturnValue({ user: null });

    const { result } = renderHook(() => useOnboardingFlow(), { wrapper });

    expect(result.current).toBeNull();
    expect(navigateMock).toHaveBeenCalledWith("/welcome", { replace: true });
  });

  test("loads registry, responses, and progress for the signed-in user", async () => {
    useCurrentUserMock.mockReturnValue({ user: { profileId: "profile-1" } });
    apiMock.getOnboardingRegistry.mockResolvedValue({
      q2: { key: "q2", n: 2, phase: 1, section: "Basics", question: "Q2", answer_type: "text" },
      q1: { key: "q1", n: 1, phase: 1, section: "Basics", question: "Q1", answer_type: "text" },
    });
    apiMock.listResponses.mockResolvedValue([{ question_key: "q1", response_value: "hello" }]);
    apiMock.getOnboardingProgress.mockResolvedValue({ phase1_pct: 10, phase2_pct: 0, phase3_pct: 0 });

    const { result } = renderHook(() => useOnboardingFlow(), { wrapper });

    await waitFor(() => expect(result.current?.loading).toBe(false));

    expect(result.current?.responses).toEqual({ q1: "hello" });
    expect(result.current?.progress).toEqual({ phase1_pct: 10, phase2_pct: 0, phase3_pct: 0 });
    expect(result.current?.sections).toHaveLength(1);
    expect(result.current?.sections[0].questions.map((question) => question.key)).toEqual(["q1", "q2"]);
  });

  test("setAnswer debounces submit and refreshes progress", async () => {
    useCurrentUserMock.mockReturnValue({ user: { profileId: "profile-1" } });
    apiMock.getOnboardingRegistry.mockResolvedValue({
      q1: { key: "q1", n: 1, phase: 1, section: "Basics", question: "Q1", answer_type: "text" },
    });
    apiMock.listResponses.mockResolvedValue([]);
    apiMock.getOnboardingProgress
      .mockResolvedValueOnce({ phase1_pct: 0, phase2_pct: 0, phase3_pct: 0 })
      .mockResolvedValueOnce({ phase1_pct: 20, phase2_pct: 0, phase3_pct: 0 });
    apiMock.submitResponse.mockResolvedValue({});

    const { result } = renderHook(() => useOnboardingFlow(), { wrapper });

    await waitFor(() => expect(result.current?.loading).toBe(false));

    act(() => {
      result.current?.setAnswer("q1", "updated", {
        key: "q1",
        n: 1,
        phase: 1,
        section: "Basics",
        question: "Q1",
        answer_type: "text",
      });
    });

    expect(result.current?.responses.q1).toBe("updated");

    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 650));
    });

    expect(apiMock.submitResponse).toHaveBeenCalledWith("profile-1", expect.objectContaining({
        question_key: "q1",
        response_value: "updated",
      }));
    await waitFor(() => {
      expect(result.current?.progress).toEqual({ phase1_pct: 20, phase2_pct: 0, phase3_pct: 0 });
    });
  });
});
