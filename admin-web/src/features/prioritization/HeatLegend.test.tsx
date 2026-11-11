import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HeatLegend } from "./HeatLegend";

describe("leyenda del mapa de calor", () => {
  it("heatmap_legend_shows_numbers: la escala lleva números, no solo color", () => {
    render(<HeatLegend />);

    const legend = screen.getByRole("group", { name: "Escala de urgencia U" });
    expect(legend).toHaveTextContent("0 · Menor");
    expect(legend).toHaveTextContent("10 · Mayor urgencia");
  });
});
