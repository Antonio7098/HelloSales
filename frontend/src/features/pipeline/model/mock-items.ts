import type { PipelineItem } from "./types";

export const mockPipelineItems: PipelineItem[] = [
  {
    id: "lead-001",
    accountName: "Northline Systems",
    contactName: "Avery Singh",
    valueLabel: "14k ARR",
    stage: "new",
  },
  {
    id: "lead-002",
    accountName: "Harbor Peak",
    contactName: "Jordan Wells",
    valueLabel: "22k ARR",
    stage: "qualified",
  },
  {
    id: "lead-003",
    accountName: "Cinder Health",
    contactName: "Mina Patel",
    valueLabel: "40k ARR",
    stage: "proposal",
  },
];
