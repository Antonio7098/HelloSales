import { useSectionFocus } from "@/shared/hooks/useSectionFocus";
import { smoothScrollTo } from "../utils/scroll";

const COMPETITIVE_GAP: Array<[string, string, string]> = [
  ["Training platforms", "Teach reps", "No execution"],
  ["Roleplay AI", "Simulate calls", "Not real"],
  ["Enablement tools", "Organize knowledge", "No enforcement"],
  ["Call AI tools", "Analyze calls", "No behavior control"],
  ["CRMs", "Track deals", "No sales intelligence"],
];

export function CompetitiveGapTable() {
  const gap = useSectionFocus<HTMLElement>();

  return (
    <section ref={gap.ref} id="section-gap" className="signup-section funnel-gap">
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
              {COMPETITIVE_GAP.map(([cat, action, miss], idx) => (
                <tr
                  key={cat}
                  className="stagger-row"
                  style={{ transitionDelay: `${100 + idx * 150}ms` }}
                >
                  <td>{cat}</td>
                  <td>{action}</td>
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
          onClick={() => smoothScrollTo("#section-book")}
          className="funnel-cta funnel-cta--ghost-light funnel-cta--240 stagger-child"
          style={{ transitionDelay: "1000ms" }}
        >
          Get started →
        </button>
      </div>
    </section>
  );
}
