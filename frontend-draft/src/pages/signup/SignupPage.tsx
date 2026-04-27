/**
 * SignupPage — demo signup form. /Oliviercontribution.
 *
 * In Sheets-mode (Vercel demo), POSTs to the Apps Script which creates a row
 * in `company_profile` + `client_contact_extension` and returns a profileId.
 * In FastAPI mode, calls upsertClientContact (no real signup endpoint exists
 * in the backend yet — company_profile is currently a singleton; we treat the
 * first signup as the founder/admin).
 *
 * After signup, stores {profileId, email, name, companyName, role} in
 * localStorage and redirects to /onboarding.
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Field,
  Input,
  PageHeader,
  Row,
  Stack,
  Surface,
  Text,
} from "@/design-system";
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

    // Always derive a stable demo profileId so localStorage works offline-first.
    const profileId = `demo-${email.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`;

    // Best-effort backend write. In demo mode (no FastAPI, no Apps Script
    // configured) this errors silently — we still sign you in so you can
    // click through the UI. The real persistence kicks in once the backend
    // or webhook is reachable.
    try {
      const api = getSalesbookApi();
      if (isSheetsMode && api.signup) {
        const res = await api.signup({ name, email, companyName, role });
        // If the webhook returns a profileId, prefer it.
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
      // Don't block the UI on demo backend failures — log and continue.
      console.warn("[signup] backend unreachable, continuing in local-only demo mode:", err);
    }

    signIn({
      profileId,
      email, name, companyName, role,
      signedUpAt: new Date().toISOString(),
    });
    navigate(role === "admin" ? "/onboarding" : "/dashboard", { replace: true });
  }

  return (
    <div className="signup-shell">
      <Surface padding="default" tone="default" className="signup-card">
        <Stack gap="lg">
          <Row gap="sm" baseline>
            <img src="/hello-sales-icon.png" alt="" style={{ width: 36, height: 36 }} />
            <PageHeader
              eyebrow="Hello Sales · sign in"
              title="Welcome to your sales operating desk"
              description="Tell us who you are. The path through the app — and the depth of your onboarding — depends on the role you pick."
            />
          </Row>

          <form onSubmit={handleSubmit}>
            <Stack gap="sm">
              <Field label="Your name">
                {({ id }) => (
                  <Input
                    id={id}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Olivier Greki"
                    required
                    autoComplete="name"
                  />
                )}
              </Field>

              <Field label="Email">
                {({ id }) => (
                  <Input
                    id={id}
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="olivier@yourcompany.com"
                    required
                    autoComplete="email"
                  />
                )}
              </Field>

              <Field label="Company name">
                {({ id }) => (
                  <Input
                    id={id}
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Acme Corp"
                    required
                    autoComplete="organization"
                  />
                )}
              </Field>

              <Field label="Role">
                {({ id }) => (
                  <div className="role-grid" id={id}>
                    <RoleCard
                      selected={role === "admin"}
                      onSelect={() => setRole("admin")}
                      title="VP / Admin"
                      subtitle="CEO · VP Sales · Founder"
                      blurb="Lays the foundation of the company's business IQ. Defines the product, the ICP, the buyer journey, and the pipeline strategy. Sees every rep, every deal, and every signal across the org."
                      tag="Detailed onboarding · 114 questions across 3 phases"
                    />
                    <RoleCard
                      selected={role === "rep"}
                      onSelect={() => setRole("rep")}
                      title="Sales rep"
                      subtitle="Account executive · BDR"
                      blurb="Runs your own pipeline of leads from the ground up. Logs every call, email, and meeting in one place so the org learns from your fieldwork."
                      tag="Lighter onboarding · personal workspace setup"
                    />
                  </div>
                )}
              </Field>

              <p className="text-body-muted text-mono" style={{ margin: 0, fontSize: 12 }}>
                In the final version VPs and reps will get separate onboarding URLs. For
                this preview the role you pick decides which path you land on.
              </p>

              {error ? (
                <p className="text-body" style={{ color: "var(--danger)", margin: 0 }}>
                  {error}
                </p>
              ) : null}

              <Row gap="sm" between>
                <Text variant="mono" className="text-body-muted">
                  {isSheetsMode ? "Demo mode · writes to Google Sheets" : "Connected to FastAPI"}
                </Text>
                <Button variant="primary" type="submit" disabled={submitting}>
                  {submitting ? "Signing in…" : "Get started →"}
                </Button>
              </Row>
            </Stack>
          </form>
        </Stack>
      </Surface>
    </div>
  );
}

function RoleCard({
  selected,
  onSelect,
  title,
  subtitle,
  blurb,
  tag,
}: {
  selected: boolean;
  onSelect: () => void;
  title: string;
  subtitle: string;
  blurb: string;
  tag: string;
}) {
  return (
    <button type="button" onClick={onSelect} className={`role-card ${selected ? "is-selected" : ""}`}>
      <Stack gap="xs">
        <Row gap="xs" between baseline>
          <span className="role-card-title">{title}</span>
          {selected ? <span className="role-card-check">✓</span> : null}
        </Row>
        <Text variant="mono" className="text-body-muted">
          {subtitle}
        </Text>
        <Text className="text-body">{blurb}</Text>
        <span className="role-card-tag">{tag}</span>
      </Stack>
    </button>
  );
}
