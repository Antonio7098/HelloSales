import type { ReactNode } from "react";
import { Text } from "@/design-system/primitives/Text";
import { cn } from "@/shared/lib/cn";

type EmptyStateProps = {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
};

export function EmptyState({
  eyebrow,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("empty-state stack-xs", className)}>
      {eyebrow ? <Text variant="eyebrow">{eyebrow}</Text> : null}
      <Text variant="subtitle" as="p">
        {title}
      </Text>
      {description ? <Text variant="bodyMuted">{description}</Text> : null}
      {action ? <div style={{ marginTop: "0.25rem" }}>{action}</div> : null}
    </div>
  );
}
