/**
 * SignupPage — split layout: brand value pitch on the left, focused form on
 * the right. /Oliviercontribution. No "templaty" centered card — the form
 * shares the canvas with brand context so the page has personality.
 *
 * Best-effort backend write; falls back to local-only signin if no backend
 * is reachable so the demo is clickable without Postgres or Apps Script.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Field, Input, Stack } from "@/design-system";
import { useCurrentUser, type UserRole } from "@/shared/auth/useCurrentUser";
import { getSalesbookApi, isSheetsMode } from "@/shared/api/salesbook";
import { IconArrow, IconArrowLeft, IconCheck } from "@/shared/icons/NavIcons";

export function SignupPage() {
  const navigate = useNavigate();
  const { signIn } = useCurrentUser();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [role, setRole] = useState<UserRole>("admin");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
    <div className="signup-split">
      {/* Left — brand pitch, sets context, full-bleed feel */}
      <aside className="signup-pitch">
        <Link to="/welcome" className="signup-back">
          <IconArrowLeft /> Back
        </Link>
        <div className="signup-pitch-eyebrow">Hello Sales · sign in</div>
        <h1 className="signup-pitch-title">
          One desk for the company's
          <br />
          <em>sales intelligence.</em>
        </h1>
        <p className="signup-pitch-sub">
          Tell us who you are. The rest of the app shapes itself around your role —
          VPs build the foundation, reps run their own pipeline.
        </p>
        <ul className="signup-pitch-list">
          <li><IconCheck /> 114-question business IQ for VPs</li>
          <li><IconCheck /> Personal pipeline + activity log for reps</li>
          <li><IconCheck /> AI agents trained on your actual sales motion</li>
        </ul>
      </aside>

      {/* Right — focused form */}
      <section className="signup-form-area">
        <form onSubmit={handleSubmit} className="signup-form">
          <Stack gap="md">
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

            <Field label="Pick your role">
              {({ id }) => (
                <div className="role-grid" id={id}>
                  <RoleCard
                    selected={role === "admin"}
                    onSelect={() => setRole("admin")}
                    title="VP / Admin"
                    subtitle="CEO · VP Sales · Founder"
                    blurb="Lays the foundation of the company's business IQ. Defines the product, the ICP, the buyer journey, and the pipeline strategy. Sees every rep, every deal, every signal."
                    tag="Detailed onboarding · 3 phases"
                  />
                  <RoleCard
                    selected={role === "rep"}
                    onSelect={() => setRole("rep")}
                    title="Sales rep"
                    subtitle="Account executive · BDR"
                    blurb="Runs your own pipeline of leads from the ground up. Logs every call, email, and meeting in one place so the org learns from your fieldwork."
                    tag="Lighter setup · personal workspace"
                  />
                </div>
              )}
            </Field>

            <p className="signup-note">
              In the full release, VPs and reps will have separate onboarding URLs so the
              flow is shaped to each path. For this preview the role you pick decides
              where you land.
            </p>

            <div className="signup-actions">
              <span className="signup-actions-meta">
                {isSheetsMode ? "Demo mode · writes to Google Sheets" : "Connecting to FastAPI"}
              </span>
              <Button variant="primary" type="submit" disabled={submitting} trailing={<IconArrow />}>
                {submitting ? "Signing in…" : "Get started"}
              </Button>
            </div>
          </Stack>
        </form>
      </section>
    </div>
  );
}

function RoleCard({
  selected, onSelect, title, subtitle, blurb, tag,
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
      <div className="role-card-top">
        <span className="role-card-title">{title}</span>
        {selected ? <IconCheck className="role-card-check" /> : null}
      </div>
      <div className="role-card-subtitle">{subtitle}</div>
      <p className="role-card-blurb">{blurb}</p>
      <span className="role-card-tag">{tag}</span>
    </button>
  );
}
