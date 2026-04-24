import {
  startTransition,
  useEffect,
  useState,
  type PropsWithChildren,
} from "react";
import { AuthContext, type AuthSession, type AuthStatus, useAuth } from "./auth-context";
import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";
import { getFrontendEnv } from "@/shared/config/env";
import { HttpRequestError, requestJson } from "@/shared/api/http-client";

type ApiEnvelope<T> = {
  ok: boolean;
  data: T;
};

async function loadSession(): Promise<AuthSession | null> {
  try {
    const payload = await requestJson<ApiEnvelope<AuthSession>>({ path: "/auth/session" });
    return payload.data;
  } catch (error) {
    if (error instanceof HttpRequestError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [session, setSession] = useState<AuthSession | null>(null);

  const refresh = async () => {
    const currentSession = await loadSession();
    startTransition(() => {
      setSession(currentSession);
      setStatus(currentSession ? "authenticated" : "anonymous");
    });
  };

  useEffect(() => {
    void refresh();
  }, []);

  const login = (returnPath = window.location.pathname + window.location.search + window.location.hash) => {
    const encoded = encodeURIComponent(returnPath);
    window.location.assign(`${getFrontendEnv().apiBaseUrl}/auth/login?return_path=${encoded}`);
  };

  const logout = async () => {
    const payload = await requestJson<ApiEnvelope<{ redirect_url: string | null }>>({
      path: "/auth/logout",
      method: "POST",
    });
    startTransition(() => {
      setSession(null);
      setStatus("anonymous");
    });
    if (payload.data.redirect_url) {
      window.location.assign(payload.data.redirect_url);
    }
  };

  return (
    <AuthContext.Provider value={{ status, session, refresh, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function RequireAuth({ children }: PropsWithChildren) {
  const auth = useAuth();

  if (auth.status === "loading") {
    return (
      <div className="auth-screen">
        <Surface>
          <div className="stack-sm">
            <Text variant="eyebrow">Secure workspace</Text>
            <Text as="h1" variant="title">
              Loading session
            </Text>
            <Text variant="bodyMuted">
              HelloSales is verifying your workspace session and permissions.
            </Text>
          </div>
        </Surface>
      </div>
    );
  }

  if (auth.status === "anonymous") {
    return (
      <div className="auth-screen">
        <Surface>
          <div className="stack-md">
            <div className="stack-sm">
              <Text variant="eyebrow">B2B access</Text>
              <Text as="h1" variant="title">
                Sign in to your sales workspace
              </Text>
              <Text variant="bodyMuted">
                Authentication and permissions are enforced by the backend before any workspace
                data or automation routes are available.
              </Text>
            </div>
            <button type="button" className="action-button" onClick={() => auth.login()}>
              Continue with SSO
            </button>
          </div>
        </Surface>
      </div>
    );
  }

  return <>{children}</>;
}
