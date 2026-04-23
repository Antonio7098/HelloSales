import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

export function Kbd({ children, className }: { children: ReactNode; className?: string }) {
  return <kbd className={cn("kbd", className)}>{children}</kbd>;
}
