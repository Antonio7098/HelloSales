import { PipelineBoard } from "@/features/pipeline/components/PipelineBoard";
import { Text } from "@/design-system/primitives/Text";

export function PipelineBoardSection() {
  return (
    <section className="stack-md">
      <Text as="h1" variant="title">
        Pipeline
      </Text>
      <Text variant="body">
        This route-level section composes the feature export instead of carrying hidden
        business logic itself.
      </Text>
      <PipelineBoard />
    </section>
  );
}
