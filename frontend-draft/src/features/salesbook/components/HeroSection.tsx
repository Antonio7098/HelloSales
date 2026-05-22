import { useEffect, useState } from "react";
import { useSectionFocus } from "@/shared/hooks/useSectionFocus";
import { smoothScrollTo } from "../utils/scroll";

const KEYWORDS = [
  "more sales IQ",
  "a salesbook",
  "pipeline intelligence",
  "scalable sales knowledge",
  "data-backed decisions",
  "institutional memory",
  "Hello Sales",
];

export function HeroSection() {
  const hero = useSectionFocus<HTMLElement>({ initialVisible: true });
  const [keywordIndex, setKeywordIndex] = useState(0);
  const [keywordPhase, setKeywordPhase] = useState<"in" | "out">("in");

  useEffect(() => {
    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) return;

    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      setKeywordPhase("out");
      window.setTimeout(() => {
        setKeywordIndex((i) => (i + 1) % KEYWORDS.length);
        setKeywordPhase("in");
      }, 200);
    }, 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <section ref={hero.ref} id="section-hero" className="signup-section funnel-hero">
      <div className={`section-content funnel-hero-inner ${hero.isVisible ? "focused" : "unfocused"}`}>
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
              {KEYWORDS[keywordIndex]}
            </span>
            <span className="hero-keyword-period">.</span>
          </div>

          <button
            type="button"
            onClick={() => smoothScrollTo("#section-gap")}
            className="funnel-cta funnel-cta--white funnel-cta--240 stagger-child"
            style={{ transitionDelay: "300ms" }}
          >
            Start Now →
          </button>
        </div>

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
  );
}
