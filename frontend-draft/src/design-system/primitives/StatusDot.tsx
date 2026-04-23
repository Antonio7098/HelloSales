import { cn } from "@/shared/lib/cn";
import type { BadgeTone } from "@/design-system/primitives/Badge";

type StatusDotTone = Exclude<BadgeTone, "outline">;

type StatusDotProps = {
  tone?: StatusDotTone;
  pulse?: boolean;
  label?: string;
  className?: string;
};

const toneClass: Record<StatusDotTone, string> = {
  neutral: "",
  accent: "dot--accent",
  success: "dot--success",
  warn: "dot--warn",
  danger: "dot--danger",
  info: "dot--info",
};

export function StatusDot({ tone = "neutral", pulse = false, label, className }: StatusDotProps) {
  return (
    <span
      className={cn("dot", toneClass[tone], pulse && "dot--pulse", className)}
      role={label ? "status" : undefined}
      aria-label={label}
    />
  );
}
