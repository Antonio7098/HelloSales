import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

export type BadgeTone = "neutral" | "accent" | "success" | "warn" | "danger" | "info" | "outline";

type BadgeProps = {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
};

const toneClass: Record<BadgeTone, string> = {
  neutral: "badge--neutral",
  accent: "badge--accent",
  success: "badge--success",
  warn: "badge--warn",
  danger: "badge--danger",
  info: "badge--info",
  outline: "badge--outline",
};

export function Badge({ tone = "neutral", children, className }: BadgeProps) {
  return <span className={cn("badge", toneClass[tone], className)}>{children}</span>;
}
