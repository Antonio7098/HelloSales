import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";

const steps = [
  "Capture lead context",
  "Assess fit and urgency",
  "Prepare a follow-up recommendation",
];

export function QualificationWorkflowPreview() {
  return (
    <Surface>
      <Text as="h2" variant="sectionTitle">
        Workflow scaffold
      </Text>
      <Text variant="body">
        Cross-feature journeys live in workflows so they stay visible and replaceable.
      </Text>
      <ol className="stack-sm ordered-list">
        {steps.map((step) => (
          <li key={step}>
            <Text variant="body">{step}</Text>
          </li>
        ))}
      </ol>
    </Surface>
  );
}
