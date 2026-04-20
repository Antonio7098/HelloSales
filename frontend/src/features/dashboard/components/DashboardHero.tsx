import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";

export function DashboardHero() {
  return (
    <Surface>
      <Text variant="eyebrow">Pre-brief frontend scaffold</Text>
      <Text as="h1" variant="hero">
        Organized for fast change when the product brief lands
      </Text>
      <Text variant="body">
        The home page is intentionally thin. Product behavior should accumulate inside
        features and workflows, not inside route files.
      </Text>
    </Surface>
  );
}
