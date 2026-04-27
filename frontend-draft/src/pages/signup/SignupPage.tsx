/**
 * SignupPage — full conversion funnel: hook → problem → solution → proof → convert.
 * /Oliviercontribution.
 *
 * One page, 5 scroll sections. Every CTA smooth-scrolls to the next section.
 * IBM Plex Mono throughout. Owns the full viewport (no PublicLayout chrome).
 *
 * Animations: hero elements fade-up on page load with stagger delays (CSS
 * keyframes). All other sections use IntersectionObserver via useScrollReveal
 * to fade in on viewport entry. Respects prefers-reduced-motion.
 *
 * Submit logic unchanged — best-effort backend write, localStorage signin
 * fallback, redirect by role (admin → /onboarding, rep → /dashboard).
 */

import { useState, useRef, type FormEvent, type RefObject } from "react";
import { useNavigate } from "react-router-dom";
import { useCurrentUser, type UserRole } from "@/shared/auth/useCurrentUser";
import { getSalesbookApi, isSheetsMode } from "@/shared/api/salesbook";
import { useScrollReveal } from "@/shared/hooks/useScrollReveal";

const COMPETITIVE_GAP: Array<[string, string, string]> = [
  ["Training platforms", "Teach reps", "No execution"],
  ["Roleplay AI", "Simulate calls", "Not real"],
  ["Enablement tools", "Organize knowledge", "No enforcement"],
  ["Call AI tools", "Analyze calls", "No behavior control"],
  ["CRMs", "Track deals", "No sales intelligence"],
];

const BOOK_LINES: string[] = [
  "provide live sales arguments during every call.",
  "provide your team with its own Salesbook.",
  "provide enhanced clarity to executives on every deal.",
  "provide AI agents ready to deploy on your pipeline.",
  "provide enterprise-level suggestions to increase net profits.",
  "provide pipeline-aware coaching for every rep.",
  "provide instant advanced onboarding for new hires.",
  "provide data on every interaction, every channel, every rep.",
  "provide structured call flows based on deal stage.",
  "provide conversion intelligence built from your own data.",
  "provide deal qualification enforcement on every opportunity.",
  "provide a living playbook that improves with every call.",
  "provide buyer persona matching for each prospect.",
  "provide automated follow-up sequences to trigger pipeline movements.",
  "provide the infrastructure to scale what your best rep already knows.",
  "provide confidence you will never lose the knowledge of your top sales reps.",
];

const CHALLENGE_ROWS: Array<[string, string, string]> = [
  ["Inconsistent rep performance", "Unpredictable revenue, missed quotas", "AI-coached calls from your salesbook"],
  ["Long ramp time for new hires", "Months of lost productivity and pipeline", "Instant onboarding from company sales IQ"],
  ["Knowledge trapped in top reps", "Risk of institutional knowledge loss", "Salesbook captures and distributes it"],
  ["Manual training and scripts", "Cannot scale, quickly outdated", "Living playbook that learns from every call"],
  ["No real-time coaching", "Reps left alone on live calls", "Live agent recommendations mid-conversation"],
];

function scrollTo(ref: RefObject<HTMLElement | null>) {
  ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function SignupPage() {
  const navigate = useNavigate();
  const { signIn } = useCurrentUser();

  // Section refs — both for smooth-scroll targets AND for reveal animation triggers
  const gapRef = useScrollReveal<HTMLElement>();
  const bookRef = useScrollReveal<HTMLElement>();
  const challengeRef = useScrollReveal<HTMLElement>();
  const formRef = useScrollReveal<HTMLElement>();

  // Smooth-scroll navigation needs plain refs alongside the reveal refs
  const gapNavRef = useRef<HTMLElement>(null);
  const bookNavRef = useRef<HTMLElement>(null);
  const challengeNavRef = useRef<HTMLElement>(null);
  const formNavRef = useRef<HTMLElement>(null);

  // Combine the two refs onto one element
  const setGap = (el: HTMLElement | null) => { gapRef.current = el; gapNavRef.current = el; };
  const setBook = (el: HTMLElement | null) => { bookRef.current = el; bookNavRef.current = el; };
  const setChallenge = (el: HTMLElement | null) => { challengeRef.current = el; challengeNavRef.current = el; };
  const setForm = (el: HTMLElement | null) => { formRef.current = el; formNavRef.current = el; };

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
    <div className="funnel">
      {/* SECTION 1 — HERO. Hero elements use .funnel-hero-anim classes that animate on page load (CSS keyframes), no IO needed. */}
      <section className="funnel-hero">
        <div className="funnel-hero-inner">
          <img
            src="/hello-sales-logo.png"
            alt="Hello Sales"
            className="funnel-brand-logo funnel-hero-anim funnel-hero-anim--logo"
          />
          <h1 className="funnel-hero-title funnel-hero-anim funnel-hero-anim--title">
            Your company needs<br />more sales IQ.
          </h1>
          <p className="funnel-hero-sub funnel-hero-anim funnel-hero-anim--sub">
            Stop losing deals to inconsistent reps, slow onboarding, and knowledge that
            leaves when your best people do.
          </p>
          <button
            type="button"
            onClick={() => scrollTo(gapNavRef)}
            className="funnel-cta funnel-cta--primary funnel-cta--240 funnel-hero-anim funnel-hero-anim--cta"
          >
            Get started →
          </button>
          <p className="funnel-hero-meta funnel-hero-anim funnel-hero-anim--cta">
            Built for sales leaders managing 5–50 reps
          </p>
        </div>
      </section>

      {/* SECTION 2 — COMPETITIVE GAP TABLE. Reveals via IO, rows stagger in. */}
      <section ref={setGap} className="funnel-gap scroll-reveal">
        <div className="funnel-gap-inner">
          <h2 className="funnel-gap-title scroll-reveal-stagger" style={{ transitionDelay: "0ms" }}>
            Every sales team has tools.
          </h2>
          <p className="funnel-gap-sub scroll-reveal-stagger" style={{ transitionDelay: "120ms" }}>
            None of them do what you actually need.
          </p>

          <div className="funnel-table-wrap">
            <table className="funnel-gap-table">
              <thead>
                <tr>
                  <th className="scroll-reveal-stagger" style={{ transitionDelay: "240ms" }}>Category</th>
                  <th className="scroll-reveal-stagger" style={{ transitionDelay: "240ms" }}>What they do</th>
                  <th className="scroll-reveal-stagger" style={{ transitionDelay: "240ms" }}>What's missing</th>
                </tr>
              </thead>
              <tbody>
                {COMPETITIVE_GAP.map(([cat, doe, miss], idx) => (
                  <tr
                    key={cat}
                    className="scroll-reveal-stagger"
                    style={{ transitionDelay: `${360 + idx * 200}ms` }}
                  >
                    <td>{cat}</td>
                    <td>{doe}</td>
                    <td className="funnel-gap-missing">{miss}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p
            className="funnel-gap-foot scroll-reveal-pop"
            style={{ transitionDelay: `${360 + COMPETITIVE_GAP.length * 200 + 120}ms` }}
          >
            Hello Sales does all five.
          </p>
          <button
            type="button"
            onClick={() => scrollTo(bookNavRef)}
            className="funnel-cta funnel-cta--ghost-light scroll-reveal-stagger"
            style={{ transitionDelay: `${360 + COMPETITIVE_GAP.length * 200 + 320}ms` }}
          >
            See what you get →
          </button>
        </div>
      </section>

      {/* SECTION 3 — BOOK PAGE (manifesto on notebook ruled lines). */}
      <section ref={setBook} className="funnel-book-section scroll-reveal">
        <article className="funnel-book scroll-reveal-tilt" aria-label="Hello Sales manifesto">
          <div className="funnel-book-margin" aria-hidden="true" />
          <div className="funnel-book-lines">
            {BOOK_LINES.map((rest, i) => (
              <div
                key={i}
                className="funnel-book-line scroll-reveal-write"
                style={{ transitionDelay: `${300 + i * 80}ms` }}
              >
                <strong>Hello Sales</strong>&nbsp;&nbsp;{rest}
              </div>
            ))}
          </div>
        </article>
        <p
          className="funnel-book-caption scroll-reveal-stagger"
          style={{ transitionDelay: `${300 + BOOK_LINES.length * 80 + 200}ms` }}
        >
          This is what your team gets on day one.
        </p>
      </section>

      {/* SECTION 4 — CHALLENGE / SOLUTION TABLE. */}
      <section ref={setChallenge} className="funnel-challenge scroll-reveal">
        <div className="funnel-challenge-inner">
          <h2 className="funnel-challenge-title scroll-reveal-stagger" style={{ transitionDelay: "0ms" }}>
            Real problems. Real answers.
          </h2>

          <div className="funnel-table-wrap">
            <table className="funnel-challenge-table">
              <thead>
                <tr>
                  <th className="th-dark scroll-reveal-stagger" style={{ transitionDelay: "200ms" }}>Challenge</th>
                  <th className="th-dark scroll-reveal-stagger" style={{ transitionDelay: "200ms" }}>Impact on Business</th>
                  <th className="th-green scroll-reveal-stagger" style={{ transitionDelay: "200ms" }}>Hello Sales</th>
                </tr>
              </thead>
              <tbody>
                {CHALLENGE_ROWS.map(([ch, im, hs], idx) => (
                  <tr
                    key={ch}
                    className={`${idx % 2 === 0 ? "row-even" : "row-odd"} scroll-reveal-stagger`}
                    style={{ transitionDelay: `${320 + idx * 200}ms` }}
                  >
                    <td>{ch}</td>
                    <td>{im}</td>
                    <td className="td-green">{hs}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            type="button"
            onClick={() => scrollTo(formNavRef)}
            className="funnel-cta funnel-cta--primary funnel-cta--280 scroll-reveal-stagger"
            style={{ transitionDelay: `${320 + CHALLENGE_ROWS.length * 200 + 200}ms` }}
          >
            Build your salesbook →
          </button>
        </div>
      </section>

      {/* SECTION 5 — SIGNUP FORM. */}
      <section ref={setForm} className="funnel-form-section scroll-reveal">
        <form onSubmit={handleSubmit} className="funnel-form">
          <h2 className="funnel-form-title scroll-reveal-stagger" style={{ transitionDelay: "0ms" }}>
            Let's build yours.
          </h2>
          <p className="funnel-form-sub scroll-reveal-stagger" style={{ transitionDelay: "100ms" }}>
            Takes 2 minutes. No credit card.
          </p>

          <div className="funnel-fields">
            <label className="funnel-field scroll-reveal-stagger" style={{ transitionDelay: "300ms" }}>
              <span className="funnel-label">Your name</span>
              <input
                className="funnel-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                required
              />
            </label>

            <label className="funnel-field scroll-reveal-stagger" style={{ transitionDelay: "450ms" }}>
              <span className="funnel-label">Email</span>
              <input
                className="funnel-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label className="funnel-field scroll-reveal-stagger" style={{ transitionDelay: "600ms" }}>
              <span className="funnel-label">Company</span>
              <input
                className="funnel-input"
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                autoComplete="organization"
                required
              />
            </label>

            <div className="funnel-field scroll-reveal-stagger" style={{ transitionDelay: "750ms" }}>
              <span className="funnel-label">Your role</span>
              <div className="funnel-roles">
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

          {error ? <div className="funnel-error">{error}</div> : null}

          <button
            type="submit"
            disabled={submitting}
            className="funnel-cta funnel-cta--primary funnel-cta--full funnel-cta--tall scroll-reveal-stagger"
            style={{ transitionDelay: "950ms" }}
          >
            {submitting ? "Signing in…" : "Get started →"}
          </button>

          <p className="funnel-form-foot scroll-reveal-stagger" style={{ transitionDelay: "1100ms" }}>
            Your data stays yours. Always.
          </p>
        </form>
      </section>
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
      className={`funnel-role ${selected ? "is-selected" : ""}`}
    >
      <span className="funnel-role-title">{title}</span>
      <span className="funnel-role-sub">{subtitle}</span>
    </button>
  );
}
