import { useSectionFocus } from "@/shared/hooks/useSectionFocus";
import { smoothScrollTo } from "../utils/scroll";

const CHALLENGE_ROWS: Array<[string, string, string]> = [
  ["Inconsistent rep performance", "Unpredictable revenue, missed quotas", "AI-coached calls from your salesbook"],
  ["Long ramp time for new hires", "Months of lost productivity and pipeline", "Instant onboarding from company sales IQ"],
  ["Knowledge trapped in top reps", "Risk of institutional knowledge loss", "Salesbook captures and distributes it"],
  ["Manual training and scripts", "Cannot scale, quickly outdated", "Living playbook that learns from every call"],
  ["No real-time coaching", "Reps left alone on live calls", "Live agent recommendations mid-conversation"],
];

export function ChallengeSolutionTable() {
  const challenge = useSectionFocus<HTMLElement>();

  return (
    <section ref={challenge.ref} id="section-challenge" className="signup-section funnel-challenge">
      <div className={`section-content funnel-challenge-inner ${challenge.isVisible ? "focused" : "unfocused"}`}>
        <h2 className="funnel-challenge-title stagger-child" style={{ transitionDelay: "0ms" }}>
          Real problems. Real answers.
        </h2>

        <div className="funnel-table-wrap stagger-child" style={{ transitionDelay: "100ms" }}>
          <table className="funnel-challenge-table">
            <caption>Common sales challenges, business impact, and Hello Sales solutions</caption>
            <thead>
              <tr>
                <th scope="col" className="th-dark">Challenge</th>
                <th scope="col" className="th-dark">Impact on Business</th>
                <th scope="col" className="th-green">Hello Sales</th>
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
          onClick={() => smoothScrollTo("#section-form")}
          className="funnel-cta funnel-cta--primary funnel-cta--240 stagger-child"
          style={{ transitionDelay: "1150ms" }}
        >
          Get started →
        </button>
      </div>
    </section>
  );
}
