import { useSectionFocus } from "@/shared/hooks/useSectionFocus";
import { useSignupForm } from "../hooks/useSignupForm";
import { RoleButton } from "./RoleButton";

export function SignupForm() {
  const form = useSectionFocus<HTMLElement>();

  const {
    name, setName,
    email, setEmail,
    companyName, setCompanyName,
    role, setRole,
    submitting,
    error,
    handleSubmit,
  } = useSignupForm();

  return (
    <section ref={form.ref} id="section-form" className="signup-section funnel-form-section">
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
  );
}
