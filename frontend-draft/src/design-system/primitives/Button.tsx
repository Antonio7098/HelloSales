import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type ButtonVariant = "primary" | "accent" | "subtle" | "ghost" | "outline";
type ButtonSize = "md" | "sm" | "icon";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leading?: ReactNode;
  trailing?: ReactNode;
};

const variantClass: Record<ButtonVariant, string> = {
  primary: "btn--primary",
  accent: "btn--accent",
  subtle: "btn--subtle",
  ghost: "btn--ghost",
  outline: "",
};

const sizeClass: Record<ButtonSize, string> = {
  md: "",
  sm: "btn--sm",
  icon: "btn--icon",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "outline", size = "md", leading, trailing, className, children, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      className={cn("btn", variantClass[variant], sizeClass[size], className)}
      {...rest}
    >
      {leading}
      {children}
      {trailing}
    </button>
  );
});
