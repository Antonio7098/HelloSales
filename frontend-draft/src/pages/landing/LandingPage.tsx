/**
 * LandingPage — the hero. /Oliviercontribution.
 *
 * What visitors see at /. Sets the value proposition before asking them to
 * sign up. Two perspectives side-by-side: VP / Founder benefits and Sales rep
 * benefits. CTA → /signup.
 */

import { Link } from "react-router-dom";
import { Button, Row, Stack, Surface } from "@/design-system";

export function LandingPage() {
  return (
    <div className="landing">
      {/* Hero band */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-hero-eyebrow">
            <img src="/hello-sales-icon.png" alt="" className="landing-hero-icon" />
            <span>Hello Sales · sales operating desk</span>
          </div>

          <h1 className="landing-hero-title">
            The sales platform that
            <br />
            <em>actually learns</em> from your team.
          </h1>

          <p className="landing-hero-sub">
            Hello Sales captures how your top reps actually sell — the buyer signals, the
            objections, the fieldwork — and turns it into AI-powered intel and agentic help
            for the rest of the team. One operating desk for the VP, one personal workspace
            for every rep.
          </p>

          <Row gap="sm" className="landing-hero-cta">
            <Link to="/signup">
              <Button variant="primary">Get started →</Button>
            </Link>
            <a href="#how" className="landing-hero-secondary">
              See how it works
            </a>
          </Row>

          <div className="landing-hero-stats">
            <Stat n="114" label="onboarding signals" />
            <Stat n="3" label="phases of business IQ" />
            <Stat n="1" label="source of sales truth" />
          </div>
        </div>
      </section>

      {/* Two-column value prop — VP and rep */}
      <section id="how" className="landing-roles">
        <div className="landing-roles-inner">
          <RoleColumn
            tone="admin"
            eyebrow="For VPs / Founders"
            title="Build your company's sales IQ — once."
            points={[
              {
                head: "Lay the foundation in 3 phases",
                body: "Onboarding-as-discovery: company, salesbook, VP-level conversion intelligence. Builds the context every agent and every rep needs.",
              },
              {
                head: "See every rep, every deal, every signal",
                body: "Macro pipeline view, all-org activity log, conversion funnel. The bird's-eye view a HubSpot dashboard wishes it gave you.",
              },
              {
                head: "Approve what becomes canon",
                body: "Reps' fieldwork and notes flow into a moderation queue. You decide what makes it into the official salesbook and what gets pinned.",
              },
              {
                head: "Agents trained on your motion, not generic templates",
                body: "The 114-question business IQ feeds the AI that briefs your reps before calls and drafts their follow-ups after.",
              },
            ]}
          />

          <RoleColumn
            tone="rep"
            eyebrow="For Sales reps"
            title="Sharper context. Less admin. Your fieldwork actually matters."
            points={[
              {
                head: "AI intelligence before every call",
                body: "Agent surfaces the salesbook entries and prior interactions relevant to the prospect — so you walk in already prepared.",
              },
              {
                head: "Personal pipeline, zero CRM bloat",
                body: "Your own deal flow, your own activity log, none of the corporate overhead. Built to feel like a salesperson's tool, not an accountant's.",
              },
              {
                head: "Log once, learn forever",
                body: "Every call, email, and meeting is captured with the WHY, the RESULT, and the NEXT step. Searchable, agent-readable, team-shareable.",
              },
              {
                head: "Your insights make the org smarter",
                body: "Add comments and field signals to any salesbook entry. Admin reviews; the best gets pinned and shared with the team.",
              },
            ]}
          />
        </div>
      </section>

      {/* Closing CTA */}
      <Surface tone="default" className="landing-final">
        <Stack gap="md">
          <h2 className="landing-final-title">Stop reinventing your sales process every quarter.</h2>
          <p className="landing-final-sub">
            Capture the playbook once. Let the agents and the team execute on it forever.
          </p>
          <Row gap="sm">
            <Link to="/signup">
              <Button variant="primary">Get started →</Button>
            </Link>
          </Row>
        </Stack>
      </Surface>
    </div>
  );
}

function Stat({ n, label }: { n: string; label: string }) {
  return (
    <div className="landing-stat">
      <div className="landing-stat-n">{n}</div>
      <div className="landing-stat-label">{label}</div>
    </div>
  );
}

function RoleColumn({
  tone,
  eyebrow,
  title,
  points,
}: {
  tone: "admin" | "rep";
  eyebrow: string;
  title: string;
  points: Array<{ head: string; body: string }>;
}) {
  return (
    <div className={`landing-role landing-role--${tone}`}>
      <div className="landing-role-eyebrow">{eyebrow}</div>
      <h2 className="landing-role-title">{title}</h2>
      <div className="landing-role-points">
        {points.map((p) => (
          <div key={p.head} className="landing-role-point">
            <div className="landing-role-point-head">{p.head}</div>
            <div className="landing-role-point-body">{p.body}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
