import { IconCheck } from "@/shared/icons/NavIcons";

export function PhaseDot({ label, active, pct }: { label: string; active: boolean; pct: number }) {
  const done = pct >= 100;
  return (
    <div className={`phase-dot ${active ? "is-active" : ""} ${done ? "is-done" : ""}`}>
      <span className="phase-dot-circle">
        {done ? <IconCheck width={12} height={12} /> : label}
      </span>
      <span className="phase-dot-label">Phase {label}</span>
      <span className="phase-dot-pct">{pct.toFixed(0)}%</span>
    </div>
  );
}
