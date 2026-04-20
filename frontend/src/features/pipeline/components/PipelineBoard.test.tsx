import { screen } from "@testing-library/react";
import { PipelineBoard } from "./PipelineBoard";
import { renderWithAppProviders } from "@/test/test-utils";

describe("PipelineBoard", () => {
  it("renders grouped pipeline stages from the feature slice", () => {
    renderWithAppProviders(<PipelineBoard />);

    expect(screen.getByText("Northline Systems")).toBeInTheDocument();
    expect(screen.getByText("Harbor Peak")).toBeInTheDocument();
    expect(screen.getByText("Cinder Health")).toBeInTheDocument();
  });
});
