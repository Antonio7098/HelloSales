import type { ElementType, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type StackGap = "3xs" | "2xs" | "xs" | "sm" | "md" | "lg";

type StackProps = {
  as?: ElementType;
  gap?: StackGap;
  className?: string;
  children: ReactNode;
};

const gapClass: Record<StackGap, string> = {
  "3xs": "stack-3xs",
  "2xs": "stack-2xs",
  xs: "stack-xs",
  sm: "stack-sm",
  md: "stack-md",
  lg: "stack-lg",
};

export function Stack({ as, gap = "sm", className, children }: StackProps) {
  const Component = as ?? "div";
  return <Component className={cn(gapClass[gap], className)}>{children}</Component>;
}

type RowProps = {
  as?: ElementType;
  gap?: "xs" | "sm" | "md" | "lg";
  between?: boolean;
  baseline?: boolean;
  wrap?: boolean;
  className?: string;
  children: ReactNode;
};

export function Row({
  as,
  gap = "sm",
  between = false,
  baseline = false,
  wrap = false,
  className,
  children,
}: RowProps) {
  const Component = as ?? "div";
  return (
    <Component
      className={cn(
        "row",
        `row--gap-${gap}`,
        between && "row--between",
        baseline && "row--baseline",
        wrap && "row--wrap",
        className,
      )}
    >
      {children}
    </Component>
  );
}
