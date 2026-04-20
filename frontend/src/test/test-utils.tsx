import type { PropsWithChildren } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

function Wrapper({ children }: PropsWithChildren) {
  return <MemoryRouter>{children}</MemoryRouter>;
}

export function renderWithAppProviders(ui: React.ReactElement) {
  return render(ui, { wrapper: Wrapper });
}
