import type { ElementType, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type TextVariant =
  | "hero"
  | "title"
  | "subtitle"
  | "sectionTitle"
  | "eyebrow"
  | "body"
  | "bodyStrong"
  | "bodyMuted"
  | "mono";

type TextProps<T extends ElementType> = {
  as?: T;
  children: ReactNode;
  variant?: TextVariant;
  className?: string;
};

const variantClassName: Record<TextVariant, string> = {
  hero: "text-hero",
  title: "text-title",
  subtitle: "text-subtitle",
  sectionTitle: "text-section-title",
  eyebrow: "text-eyebrow",
  body: "text-body",
  bodyStrong: "text-body-strong",
  bodyMuted: "text-body-muted",
  mono: "text-mono",
};

export function Text<T extends ElementType = "p">({
  as,
  children,
  variant = "body",
  className,
}: TextProps<T>) {
  const Component = as ?? "p";
  return (
    <Component className={cn("text", variantClassName[variant], className)}>{children}</Component>
  );
}
