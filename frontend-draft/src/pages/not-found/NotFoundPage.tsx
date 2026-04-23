import { Link } from "react-router-dom";
import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";

export function NotFoundPage() {
  return (
    <Surface>
      <Text variant="eyebrow">404</Text>
      <Text as="h1" variant="title">
        Not found
      </Text>
      <Link to="/">Return home</Link>
    </Surface>
  );
}
