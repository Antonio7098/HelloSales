import { cn } from "@/shared/lib/cn";

type DividerProps = {
  dashed?: boolean;
  className?: string;
};

export function Divider({ dashed = false, className }: DividerProps) {
  return (
    <hr
      className={cn("divider", dashed && "divider--dashed", className)}
      role="separator"
      aria-orientation="horizontal"
    />
  );
}
