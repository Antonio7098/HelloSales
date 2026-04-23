export type ApiEnvelope<T> = {
  ok: true;
  data: T;
};

export type DashboardDataEntry = {
  entry_id: string;
  dataset_key: string;
  sequence_no: number;
  section_label: string;
  prompt_text: string;
  answer_type: string;
  example_answer: string;
};

export type DashboardDataSection = {
  dataset_key: string;
  section_label: string;
  entries: DashboardDataEntry[];
};

export type DashboardDataResponse = {
  total_entries: number;
  sections: DashboardDataSection[];
};
