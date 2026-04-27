/**
 * SignupPage — premium minimal mono. /Oliviercontribution.
 *
 * Single centered column. No card, no marketing column, no badges, no bullet
 * list. IBM Plex Mono everywhere. Bottom-border inputs. Black submit button.
 * Owns its full viewport (not wrapped in PublicLayout).
 *
 * Submission logic preserved from prior version: best-effort backend write,
 * fall back to localStorage-only signin if no backend is reachable.
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useCurrentUser, type UserRole } from "@/shared/auth/useCurrentUser";
import { getSalesbookApi, isSheetsMode } from "@/shared/api/salesbook";

export function SignupPage() {
  const navigate = useNavigate();
  const { signIn } = useCurrentUser();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [role, setRole] = useState<UserRole>("admin");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    const profileId = `demo-${email.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`;
    try {
      const api = getSalesbookApi();
      if (isSheetsMode && api.signup) {
        const res = await api.signup({ name, email, companyName, role });
        if (res?.profileId) {
          signIn({
            profileId: res.profileId,
            email, name, companyName, role,
            signedUpAt: new Date().toISOString(),
          });
          navigate(role === "admin" ? "/onboarding" : "/dashboard", { replace: true });
          return;
        }
      } else {
        await api.upsertClientContact(profileId, {
          primary_email: email,
          contact_name: name,
          contact_role: role === "admin" ? "Founder/VP" : "Sales Rep",
          phone: null,
          company_size: null,
          geography: null,
          status: "active",
        });
      }
    } catch (err) {
      // Silent fallback — proceed to localStorage signin even if backend is down.
      // Only surface an error if the user explicitly retries and it still fails.
      console.warn("[signup] backend unreachable, continuing in local-only demo mode:", err);
    }

    try {
      signIn({
        profileId,
        email, name, companyName, role,
        signedUpAt: new Date().toISOString(),
      });
      navigate(role === "admin" ? "/onboarding" : "/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in.");
      setSubmitting(false);
    }
  }

  return (
    <div className="signup-mono">
      <form className="signup-mono-col" onSubmit={handleSubmit}>
        <div className="signup-mono-brand">
          HelloSales<span className="signup-mono-caret">_</span>
        </div>
        <p className="signup-mono-tagline">One desk for your sales intelligence.</p>

        <div className="signup-mono-fields">
          <label className="signup-mono-field">
            <span className="signup-mono-label">Your name</span>
            <input
              className="signup-mono-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              required
            />
          </label>

          <label className="signup-mono-field">
            <span className="signup-mono-label">Email</span>
            <input
              className="signup-mono-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>

          <label className="signup-mono-field">
            <span className="signup-mono-label">Company</span>
            <input
              className="signup-mono-input"
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              autoComplete="organization"
              required
            />
          </label>

          <div className="signup-mono-field">
            <span className="signup-mono-label">Your role</span>
            <div className="signup-mono-roles">
              <RoleButton
                selected={role === "admin"}
                onClick={() => setRole("admin")}
                title="VP / Admin"
                subtitle="Build the salesbook"
              />
              <RoleButton
                selected={role === "rep"}
                onClick={() => setRole("rep")}
                title="Sales Rep"
                subtitle="Run your pipeline"
              />
            </div>
          </div>
        </div>

        {error ? <div className="signup-mono-error">{error}</div> : null}

        <button type="submit" className="signup-mono-submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Get started →"}
        </button>
      </form>
    </div>
  );
}

function RoleButton({
  selected, onClick, title, subtitle,
}: {
  selected: boolean;
  onClick: () => void;
  title: string;
  subtitle: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={`signup-mono-role ${selected ? "is-selected" : ""}`}
    >
      <span className="signup-mono-role-title">{title}</span>
      <span className="signup-mono-role-sub">{subtitle}</span>
    </button>
  );
}
