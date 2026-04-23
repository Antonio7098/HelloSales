import type { ReactNode } from "react";
import { Text } from "@/design-system/primitives/Text";
import { cn } from "@/shared/lib/cn";

type PageHeaderProps = {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  meta?: ReactNode;
  className?: string;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  meta,
  className,
}: PageHeaderProps) {
  return (
    <header className={cn("page-header", className)}>
      {eyebrow ? <Text variant="eyebrow">{eyebrow}</Text> : null}
      <div className="page-header-row">
        <div className="stack-2xs" style={{ minWidth: 0, maxWidth: "58ch" }}>
          <Text as="h1" variant="title">
            {title}
          </Text>
          {description ? <Text variant="bodyMuted">{description}</Text> : null}
        </div>
        {actions ? <div className="row row--gap-sm row--wrap">{actions}</div> : null}
      </div>
      {meta ? <div className="page-header-meta">{meta}</div> : null}
    </header>
  );
}
