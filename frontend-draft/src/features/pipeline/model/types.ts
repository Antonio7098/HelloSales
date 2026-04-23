export type PipelineStage = "new" | "qualified" | "proposal";

export type PipelineItem = {
  id: string;
  accountName: string;
  contactName: string;
  valueLabel: string;
  stage: PipelineStage;
};
