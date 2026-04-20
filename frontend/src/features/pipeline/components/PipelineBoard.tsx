import { mockPipelineItems } from "@/features/pipeline/model/mock-items";
import type { PipelineStage } from "@/features/pipeline/model/types";
import { EntityBadge } from "@/entities/account";
import { Surface } from "@/design-system/primitives/Surface";
import { Text } from "@/design-system/primitives/Text";

const orderedStages: PipelineStage[] = ["new", "qualified", "proposal"];

export function PipelineBoard() {
  return (
    <div className="board-grid">
      {orderedStages.map((stage) => {
        const items = mockPipelineItems.filter((item) => item.stage === stage);

        return (
          <Surface key={stage}>
            <Text as="h2" variant="sectionTitle">
              {stage}
            </Text>
            <div className="stack-sm">
              {items.map((item) => (
                <div key={item.id} className="stack-xs">
                  <EntityBadge label={item.accountName} />
                  <Text variant="bodyStrong">{item.contactName}</Text>
                  <Text variant="bodyMuted">{item.valueLabel}</Text>
                </div>
              ))}
            </div>
          </Surface>
        );
      })}
    </div>
  );
}
