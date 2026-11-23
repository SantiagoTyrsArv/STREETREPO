import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderScreen } from "../../test/render";
import { ComparisonPage } from "./ComparisonPage";

vi.mock("./ZonesMap", () => ({ ZonesMap: () => <p>Contenido de zonas</p> }));
vi.mock("./RoundsPanel", () => ({ RoundsPanel: () => <p>Contenido de rondas</p> }));
vi.mock("./ResultsPanel", () => ({ ResultsPanel: () => <p>Contenido de resultados</p> }));

describe("pantalla Comparación", () => {
  it("abre en Zonas y cambia de pestaña con clic", async () => {
    renderScreen(<ComparisonPage />);

    expect(
      screen.getByRole("heading", { name: "Comparación con el panel de referencia" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Zonas" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Zonas" })).toHaveTextContent("Contenido de zonas");

    await userEvent.click(screen.getByRole("tab", { name: "Rondas" }));

    expect(screen.getByRole("tabpanel", { name: "Rondas" })).toHaveTextContent(
      "Contenido de rondas",
    );
    expect(screen.queryByText("Contenido de zonas")).toBeNull();
  });

  it("las flechas del teclado recorren las pestañas", async () => {
    renderScreen(<ComparisonPage />);

    screen.getByRole("tab", { name: "Zonas" }).focus();
    await userEvent.keyboard("{ArrowRight}");

    expect(screen.getByRole("tab", { name: "Rondas" })).toHaveFocus();
    expect(screen.getByRole("tab", { name: "Rondas" })).toHaveAttribute("aria-selected", "true");

    await userEvent.keyboard("{ArrowLeft}{ArrowLeft}");

    expect(screen.getByRole("tab", { name: "Resultados" })).toHaveFocus();
  });
});
