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
    try {
      const api = getSalesbookApi();
      let profileId: string;
      if (isSheetsMode && api.signup) {
        const res = await api.signup({ name, email, companyName, role });
        profileId = res.profileId;
      } else {
        // FastAPI demo path: derive a stable demo profileId from the email
        profileId = `demo-${email.replace(/[^a-z0-9]/gi, "-").toLowerCase()}`;
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
      signIn({
        profileId,
        email,
        name,
        companyName,
        role,
        signedUpAt: new Date().toISOString(),
      });
      // Admin → onboarding wizard; rep → dashboard (admin onboards the company)
      navigate(role === "admin" ? "/onboarding" : "/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="signup-shell">
      <Surface padding="default" tone="default" className="signup-card">
        <Stack gap="md">
          <Row gap="sm" baseline>
            <img src="/hello-sales-icon.png" alt="" style={{ width: 36, height: 36 }} />
            <PageHeader
              eyebrow="Hello Sales · sign in"
              title="Welcome to your sales operating desk"
              description="Tell us who you are. Admins (CEO / VP Sales) get the keys to the company salesbook. Reps log activity, comment on the salesbook, and run their personal pipeline."
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
                      title="Admin"
                      subtitle="CEO / VP Sales"
                      blurb="Owns the company salesbook. Sees all reps, all deals. Approves rep contributions. Marks sticky content."
                    />
                    <RoleCard
                      selected={role === "rep"}
                      onSelect={() => setRole("rep")}
                      title="Sales rep"
                      subtitle="Account executive"
                      blurb="Personal lead workspace. Logs every interaction. Comments on the salesbook to feed admin approval."
                    />
                  </div>
                )}
              </Field>

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
}: {
  selected: boolean;
  onSelect: () => void;
  title: string;
  subtitle: string;
  blurb: string;
}) {
  return (
    <button type="button" onClick={onSelect} className={`role-card ${selected ? "is-selected" : ""}`}>
      <Stack gap="2xs">
        <Row gap="xs" between baseline>
          <span className="role-card-title">{title}</span>
          {selected ? <span className="role-card-check">✓</span> : null}
        </Row>
        <Text variant="mono" className="text-body-muted">
          {subtitle}
        </Text>
        <Text className="text-body">{blurb}</Text>
      </Stack>
    </button>
  );
}
