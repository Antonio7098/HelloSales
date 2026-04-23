import { cn } from "@/shared/lib/cn";

type SkeletonProps = {
  width?: string | number;
  height?: string | number;
  radius?: string | number;
  className?: string;
};

export function Skeleton({ width = "100%", height = "1rem", radius, className }: SkeletonProps) {
  return (
    <span
      className={cn("skeleton", className)}
      style={{
        display: "block",
        width,
        height,
        borderRadius: radius,
      }}
      aria-hidden="true"
    />
  );
}
