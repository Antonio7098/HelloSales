import type { ElementType, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type TextVariant =
  | "hero"
  | "title"
  | "sectionTitle"
  | "eyebrow"
  | "body"
  | "bodyStrong"
  | "bodyMuted";

type TextProps<T extends ElementType> = {
  as?: T;
  children: ReactNode;
  variant?: TextVariant;
};

const variantClassName: Record<TextVariant, string> = {
  hero: "text-hero",
  title: "text-title",
  sectionTitle: "text-section-title",
  eyebrow: "text-eyebrow",
  body: "text-body",
  bodyStrong: "text-body-strong",
  bodyMuted: "text-body-muted",
};

export function Text<T extends ElementType = "p">({
  as,
  children,
  variant = "body",
}: TextProps<T>) {
  const Component = as ?? "p";

  return <Component className={cn("text", variantClassName[variant])}>{children}</Component>;
}
