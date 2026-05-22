import { useSectionFocus } from "@/shared/hooks/useSectionFocus";

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

export function ManifestoSection() {
  const book = useSectionFocus<HTMLElement>();

  return (
    <section ref={book.ref} id="section-book" className="signup-section funnel-book-section">
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
  );
}
