import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type MetricProps = {
  label: ReactNode;
  value: ReactNode;
  note?: ReactNode;
  className?: string;
};

export function Metric({ label, value, note, className }: MetricProps) {
  return (
    <div className={cn("metric", className)}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {note ? <span className="metric-note">{note}</span> : null}
    </div>
  );
}

export function MetricGrid({ children }: { children: ReactNode }) {
  return <div className="metric-grid">{children}</div>;
}
