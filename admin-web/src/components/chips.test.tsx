import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReviewRoadChip } from "./ReviewRoadChip";
import { SeverityChip } from "./SeverityChip";
import { StatusChip } from "./StatusChip";

describe("chips", () => {
  it("el chip de estado muestra su texto", () => {
    render(<StatusChip status="evaluado" />);
    expect(screen.getByText("Evaluado")).toBeInTheDocument();
  });

  it("cada estado tiene su propia variante visual", () => {
    render(
      <>
        <StatusChip status="registrado" />
        <StatusChip status="reparado" />
      </>,
    );
    expect(screen.getByText("Registrado")).toHaveAttribute("data-status", "registrado");
    expect(screen.getByText("Reparado")).toHaveAttribute("data-status", "reparado");
  });

  it("el chip de severidad muestra su texto", () => {
    render(<SeverityChip severity="alta" />);
    expect(screen.getByText("Alta")).toHaveAttribute("data-severity", "alta");
  });

  it("el chip de revisar vía muestra su texto", () => {
    render(<ReviewRoadChip />);
    expect(screen.getByText("Revisar vía")).toBeInTheDocument();
  });
});
