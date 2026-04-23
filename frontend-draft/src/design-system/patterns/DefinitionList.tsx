import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";

type DefinitionItem = {
  term: ReactNode;
  description: ReactNode;
};

export function DefinitionList({
  items,
  className,
}: {
  items: DefinitionItem[];
  className?: string;
}) {
  return (
    <dl className={cn("dl", className)}>
      {items.map((item, idx) => (
        <DefinitionRow key={idx} term={item.term} description={item.description} />
      ))}
    </dl>
  );
}

function DefinitionRow({ term, description }: DefinitionItem) {
  return (
    <>
      <dt>{term}</dt>
      <dd>{description}</dd>
    </>
  );
}
