/**
 * SignupPage — full conversion funnel with full-section scroll-snap focus.
 * /Oliviercontribution.
 *
 * 5 sections, each owning a full viewport (100vh). Hard scroll-snap on
 * desktop, proximity on mobile. Each section's content fades in when it
 * enters the viewport (re-triggerable: scroll back up = fades back in).
 * Internal element stagger via inline transition-delay.
 *
 * Hero rotates a keyword every 3s (paused when tab hidden). Persistent
 * top-left logo across all sections, switches to a white silhouette over
 * the dark competitive-gap section.
 *
 * IBM Plex Mono throughout. Submit logic preserved (best-effort backend
 * write, localStorage signin fallback, redirect by role).
 */

import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type RefObject,
} from "react";
import { useNavigate } from "react-router-dom";
import { useCurrentUser, type UserRole } from "@/shared/auth/useCurrentUser";
import { getSalesbookApi, isSheetsMode } from "@/shared/api/salesbook";
import { useSectionFocus } from "@/shared/hooks/useSectionFocus";

const HERO_KEYWORDS = [
  "more sales IQ",
  "a salesbook",
  "pipeline intelligence",
  "scalable sales knowledge",
  "data-backed decisions",
  "institutional memory",
  "Hello Sales",
];

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

function smoothScrollTo(ref: RefObject<HTMLElement | null>) {
  ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function SignupPage() {
  const navigate = useNavigate();
  const { signIn } = useCurrentUser();

  // Section refs — IO-backed focus state for fade in/out
  const hero = useSectionFocus<HTMLElement>({ initialVisible: true });
  const gap = useSectionFocus<HTMLElement>();
  const book = useSectionFocus<HTMLElement>();
  const challenge = useSectionFocus<HTMLElement>();
  const form = useSectionFocus<HTMLElement>();

  // Rotating hero keyword — 3s interval, two-phase fade. Pauses when tab is hidden.
  const [keywordIndex, setKeywordIndex] = useState(0);
  const [keywordPhase, setKeywordPhase] = useState<"in" | "out">("in");
  useEffect(() => {
    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return; // no rotation for reduced-motion users

    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      setKeywordPhase("out");
      window.setTimeout(() => {
        setKeywordIndex((i) => (i + 1) % HERO_KEYWORDS.length);
        setKeywordPhase("in");
      }, 200);
    }, 3000);
    return () => clearInterval(id);
  }, []);

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
    <div className="signup-page">
      {/* SECTION 1 — HERO. Dark band. Top: logo + one-line headline + CTA.
          Bottom: sub-copy + qualifier (pinned to viewport bottom). */}
      <section ref={hero.ref} className="signup-section funnel-hero">
        <div className={`section-content funnel-hero-inner ${hero.isVisible ? "focused" : "unfocused"}`}>
          {/* Main centered group */}
          <div className="hero-main">
            <img
              src="/HS.OL.removed.png"
              alt="Hello Sales"
              className="funnel-hero-logo stagger-child"
              style={{ transitionDelay: "0ms" }}
            />

            <div className="hero-headline stagger-child" style={{ transitionDelay: "150ms" }}>
              <span className="hero-prefix">Your company needs </span>
              <span className="hero-keyword" data-phase={keywordPhase}>
                {HERO_KEYWORDS[keywordIndex]}
              </span>
              <span className="hero-keyword-period">.</span>
            </div>

            <button
              type="button"
              onClick={() => smoothScrollTo(gap.ref)}
              className="funnel-cta funnel-cta--white funnel-cta--240 stagger-child"
              style={{ transitionDelay: "300ms" }}
            >
              Start Now →
            </button>
          </div>

          {/* Footer pinned to viewport bottom */}
          <div className="hero-footer">
            <p className="funnel-hero-sub stagger-child" style={{ transitionDelay: "450ms" }}>
              The bigger your team, the harder it is to keep every rep aligned, coached,
              and closing with the same playbook. <strong>Hello Sales</strong> fixes that.
            </p>
            <div className="funnel-hero-meta-chip stagger-child" style={{ transitionDelay: "550ms" }}>
              For ambitious sales teams looking to build Sales IP and maximize performance.
            </div>
          </div>
        </div>
      </section>

      {/* SECTION 2 — COMPETITIVE GAP TABLE (dark) */}
      <section ref={gap.ref} className="signup-section funnel-gap">
        <div className={`section-content funnel-gap-inner ${gap.isVisible ? "focused" : "unfocused"}`}>
          <h2 className="funnel-gap-title stagger-child" style={{ transitionDelay: "0ms" }}>
            Every sales team has tools.
          </h2>
          <p className="funnel-gap-sub stagger-child" style={{ transitionDelay: "100ms" }}>
            None of them do what you actually need.
          </p>

          <div className="funnel-table-wrap stagger-child" style={{ transitionDelay: "200ms" }}>
            <table className="funnel-gap-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>What they do</th>
                  <th>What's missing</th>
                </tr>
              </thead>
              <tbody>
                {COMPETITIVE_GAP.map(([cat, doe, miss], idx) => (
                  <tr
                    key={cat}
                    className="stagger-row"
                    style={{ transitionDelay: `${100 + idx * 150}ms` }}
                  >
                    <td>{cat}</td>
                    <td>{doe}</td>
                    <td className="funnel-gap-missing">{miss}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="funnel-gap-foot stagger-child" style={{ transitionDelay: "900ms" }}>
            Hello Sales does all five.
          </p>
          <button
            type="button"
            onClick={() => smoothScrollTo(book.ref)}
            className="funnel-cta funnel-cta--ghost-light funnel-cta--240 stagger-child"
            style={{ transitionDelay: "1000ms" }}
          >
            Get started →
          </button>
        </div>
      </section>

      {/* SECTION 3 — BOOK PAGE (notebook manifesto) */}
      <section ref={book.ref} className="signup-section funnel-book-section">
        <div className={`section-content funnel-book-stack ${book.isVisible ? "focused" : "unfocused"}`}>
          <article className="funnel-book stagger-tilt" style={{ transitionDelay: "0ms" }} aria-label="Hello Sales manifesto">
            <div className="funnel-book-margin" aria-hidden="true" />
            <div className="funnel-book-lines">
              {BOOK_LINES.map((rest, i) => (
                <div
                  key={i}
                  className="funnel-book-line stagger-write"
                  style={{ transitionDelay: `${200 + i * 60}ms` }}
                >
                  <strong>Hello Sales</strong>&nbsp;&nbsp;{rest}
                </div>
              ))}
            </div>
          </article>
          <p
            className="funnel-book-caption stagger-child"
            style={{ transitionDelay: "1300ms" }}
          >
            This is what your team gets on day one.
          </p>
        </div>
      </section>

      {/* SECTION 4 — CHALLENGE / SOLUTION TABLE */}
      <section ref={challenge.ref} className="signup-section funnel-challenge">
        <div className={`section-content funnel-challenge-inner ${challenge.isVisible ? "focused" : "unfocused"}`}>
          <h2 className="funnel-challenge-title stagger-child" style={{ transitionDelay: "0ms" }}>
            Real problems. Real answers.
          </h2>

          <div className="funnel-table-wrap stagger-child" style={{ transitionDelay: "100ms" }}>
            <table className="funnel-challenge-table">
              <thead>
                <tr>
                  <th className="th-dark">Challenge</th>
                  <th className="th-dark">Impact on Business</th>
                  <th className="th-green">Hello Sales</th>
                </tr>
              </thead>
              <tbody>
                {CHALLENGE_ROWS.map(([ch, im, hs], idx) => (
                  <tr
                    key={ch}
                    className={`${idx % 2 === 0 ? "row-even" : "row-odd"} stagger-row`}
                    style={{ transitionDelay: `${200 + idx * 150}ms` }}
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
            onClick={() => smoothScrollTo(form.ref)}
            className="funnel-cta funnel-cta--primary funnel-cta--240 stagger-child"
            style={{ transitionDelay: "1150ms" }}
          >
            Get started →
          </button>
        </div>
      </section>

      {/* SECTION 5 — SIGNUP FORM */}
      <section ref={form.ref} className="signup-section funnel-form-section">
        <form onSubmit={handleSubmit} className={`section-content funnel-form ${form.isVisible ? "focused" : "unfocused"}`}>
          <h2 className="funnel-form-title stagger-child" style={{ transitionDelay: "0ms" }}>
            Let's build yours.
          </h2>
          <p className="funnel-form-sub stagger-child" style={{ transitionDelay: "100ms" }}>
            Fix your sales foundations now.
          </p>

          <div className="funnel-fields">
            <label className="funnel-field stagger-child" style={{ transitionDelay: "200ms" }}>
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

            <label className="funnel-field stagger-child" style={{ transitionDelay: "320ms" }}>
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

            <label className="funnel-field stagger-child" style={{ transitionDelay: "440ms" }}>
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

            <div className="funnel-field stagger-child" style={{ transitionDelay: "600ms" }}>
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
            className="funnel-cta funnel-cta--primary funnel-cta--full funnel-cta--tall stagger-child"
            style={{ transitionDelay: "750ms" }}
          >
            {submitting ? "Signing in…" : "Start now →"}
          </button>

          <p className="funnel-form-foot stagger-child" style={{ transitionDelay: "850ms" }}>
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
