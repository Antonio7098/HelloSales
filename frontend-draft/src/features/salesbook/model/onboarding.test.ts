import { groupBySection, pctNumber } from "./onboarding";
import type { Registry } from "@/entities/salesbook/types";

describe("salesbook onboarding model", () => {
  test("groupBySection groups by phase and section and sorts questions", () => {
    const registry: Registry = {
      q3: { key: "q3", n: 3, phase: 2, section: "Discovery", question: "Q3", answer_type: "text" },
      q1: { key: "q1", n: 2, phase: 1, section: "Basics", question: "Q1", answer_type: "text" },
      q2: { key: "q2", n: 1, phase: 1, section: "Basics", question: "Q2", answer_type: "text" },
    };

    const groups = groupBySection(registry);

    expect(groups).toHaveLength(2);
    expect(groups[0].phase).toBe(1);
    expect(groups[0].section).toBe("Basics");
    expect(groups[0].questions.map((question) => question.key)).toEqual(["q2", "q1"]);
    expect(groups[1].phase).toBe(2);
    expect(groups[1].section).toBe("Discovery");
  });

  test("pctNumber normalizes nullish and string values", () => {
    expect(pctNumber(undefined)).toBe(0);
    expect(pctNumber(null)).toBe(0);
    expect(pctNumber("12.5")).toBe(12.5);
    expect(pctNumber(25)).toBe(25);
  });
});
