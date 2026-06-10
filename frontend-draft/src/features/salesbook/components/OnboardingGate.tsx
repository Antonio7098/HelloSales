/**
 * OnboardingGate — shown on app surfaces when onboarding isn't complete.
 * /Oliviercontribution.
 *
 * "Finish onboarding to create your company salesbook." Drops the user
 * straight into the onboarding flow. Shows partial progress if they've
 * started.
 */

import { Link } from "react-router-dom";
import { IconArrow } from "@/shared/icons/NavIcons";

type Props = {
  /** What this surface is, e.g. "salesbook" or "dashboard". */
  surface?: string;
  /** 0–100 completion. */
  pct?: number;
  answered?: number;
  total?: number;
};

export function OnboardingGate({ surface = "salesbook", pct = 0, answered = 0, total = 0 }: Props) {
  const started = answered > 0;
  return (
    <div className="onboarding-gate">
      <div className="onboarding-gate-eyebrow">Hello Sales · {surface}</div>
      <h1 className="onboarding-gate-title">
        Finish onboarding to create your company salesbook
      </h1>
      <p className="onboarding-gate-sub">
        Your salesbook is built from your onboarding answers — the product, the buyers,
        the objections, the playbook. {started ? "You're partway there." : "It only takes a few minutes."} Complete
        onboarding and this page fills itself in.
      </p>

      {started ? (
        <>
          <div className="onboarding-gate-bar" aria-hidden="true">
            <span style={{ width: `${Math.max(2, Math.min(100, pct))}%` }} />
          </div>
          <div className="onboarding-gate-meta">
            {answered}/{total} answered · {Math.round(pct)}% complete
          </div>
        </>
      ) : null}

      <Link to="/onboarding" className="onboarding-gate-btn">
        {started ? "Continue onboarding" : "Start onboarding"} <IconArrow />
      </Link>
    </div>
  );
}
