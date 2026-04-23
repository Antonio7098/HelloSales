import type { ElementType, ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type SurfaceTone = "default" | "bare" | "sunk";
type SurfacePadding = "default" | "tight" | "flush";

type SurfaceProps = {
  as?: ElementType;
  tone?: SurfaceTone;
  padding?: SurfacePadding;
  className?: string;
  children: ReactNode;
};

const toneClass: Record<SurfaceTone, string> = {
  default: "",
  bare: "surface--bare",
  sunk: "surface--sunk",
};

const paddingClass: Record<SurfacePadding, string> = {
  default: "",
  tight: "surface--tight",
  flush: "surface--flush",
};

export function Surface({
  as,
  tone = "default",
  padding = "default",
  className,
  children,
}: SurfaceProps) {
  const Component = as ?? "section";
  return (
    <Component className={cn("surface", toneClass[tone], paddingClass[padding], className)}>
      {children}
    </Component>
  );
}
