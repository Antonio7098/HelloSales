import { renderHook, act, waitFor } from "@testing-library/react";
import type { FormEvent } from "react";

const navigateMock = vi.fn();
const signInMock = vi.fn();
const upsertClientContactMock = vi.fn();
const signupMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("@/shared/auth/useCurrentUser", () => ({
  useCurrentUser: () => ({ signIn: signInMock }),
}));

vi.mock("../api/salesbook-api", () => ({
  getSalesbookApi: () => ({ upsertClientContact: upsertClientContactMock, signup: signupMock }),
  isSheetsMode: false,
}));

import { MemoryRouter } from "react-router-dom";
import { useSignupForm } from "./useSignupForm";

function wrapper({ children }: { children: React.ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>;
}

function buildEvent(): FormEvent<HTMLFormElement> {
  return {
    preventDefault: vi.fn(),
  } as unknown as FormEvent<HTMLFormElement>;
}

describe("useSignupForm", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    signInMock.mockReset();
    upsertClientContactMock.mockReset();
    signupMock.mockReset();
  });

  test("submits fastapi contact data then signs in and redirects admins", async () => {
    upsertClientContactMock.mockResolvedValue({});

    const { result } = renderHook(() => useSignupForm(), { wrapper });

    act(() => {
      result.current.setName("Ada");
      result.current.setEmail("ada@example.com");
      result.current.setCompanyName("Acme");
      result.current.setRole("admin");
    });

    await act(async () => {
      await result.current.handleSubmit(buildEvent());
    });

    expect(upsertClientContactMock).toHaveBeenCalledWith("demo-ada-example-com", expect.objectContaining({
      primary_email: "ada@example.com",
      contact_name: "Ada",
      contact_role: "Founder/VP",
    }));
    expect(signInMock).toHaveBeenCalledWith(expect.objectContaining({ profileId: "demo-ada-example-com", companyName: "Acme" }));
    expect(navigateMock).toHaveBeenCalledWith("/onboarding", { replace: true });
  });

  test("falls back to local sign-in when backend upsert fails", async () => {
    upsertClientContactMock.mockRejectedValue(new Error("offline"));

    const { result } = renderHook(() => useSignupForm(), { wrapper });

    act(() => {
      result.current.setName("Bea");
      result.current.setEmail("bea@example.com");
      result.current.setCompanyName("Beta");
      result.current.setRole("rep");
    });

    await act(async () => {
      await result.current.handleSubmit(buildEvent());
    });

    expect(signInMock).toHaveBeenCalledWith(expect.objectContaining({ profileId: "demo-bea-example-com" }));
    expect(navigateMock).toHaveBeenCalledWith("/dashboard", { replace: true });
  });

  test("surfaces sign-in errors and clears submitting state", async () => {
    upsertClientContactMock.mockResolvedValue({});
    signInMock.mockImplementation(() => {
      throw new Error("Could not save user");
    });

    const { result } = renderHook(() => useSignupForm(), { wrapper });

    act(() => {
      result.current.setName("Cara");
      result.current.setEmail("cara@example.com");
      result.current.setCompanyName("Gamma");
    });

    await act(async () => {
      await result.current.handleSubmit(buildEvent());
    });

    await waitFor(() => {
      expect(result.current.error).toBe("Could not save user");
      expect(result.current.submitting).toBe(false);
    });
  });
});
