import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderScreen } from "../../test/render";
import type { RankingItem } from "./api";
import { ESTUDIANTES, OBONUCO } from "./fixtures";
import { RankingTable } from "./RankingTable";

function renderTable(items: RankingItem[] = [ESTUDIANTES, OBONUCO], offset = 0) {
  renderScreen(<RankingTable items={items} offset={offset} />);
}

function rowOf(address: string): HTMLElement {
  const row = screen.getByRole("link", { name: address }).closest("tr");
  if (!row) {
    throw new Error(`No hay fila para ${address}`);
  }
  return row;
}

describe("tabla del ranking", () => {
  it("renders_ranking_with_comma_decimals: S, F, P y U con coma y dos decimales", () => {
    renderTable();

    const cells = within(rowOf("Av. Los Estudiantes"))
      .getAllByRole("cell")
      .map((cell) => cell.textContent);

    expect(cells.slice(-4)).toEqual(["10,00", "7,00", "8,00", "8,70"]);
  });

  it("muestra posición, chips con texto, confirmaciones y fecha corta", () => {
    renderTable();

    const row = within(rowOf("Av. Los Estudiantes"));
    expect(row.getAllByRole("cell")[0]).toHaveTextContent("1");
    expect(row.getByText("Evaluado")).toBeInTheDocument();
    expect(row.getByText("Alta")).toBeInTheDocument();
    expect(row.getByText("3 confirmaciones")).toBeInTheDocument();
    expect(row.getByText("13 oct")).toBeInTheDocument();
    expect(within(rowOf("Sin vía asociada")).getByText("1 confirmación")).toBeInTheDocument();
  });

  it("la posición continúa en las páginas siguientes", () => {
    renderTable([ESTUDIANTES], 20);

    expect(within(rowOf("Av. Los Estudiantes")).getAllByRole("cell")[0]).toHaveTextContent("21");
  });

  it("shows_review_road_chip: solo en los reportes sin vía", () => {
    renderTable();

    expect(within(rowOf("Sin vía asociada")).getByText("Revisar vía")).toBeInTheDocument();
    expect(within(rowOf("Av. Los Estudiantes")).queryByText("Revisar vía")).toBeNull();
  });

  it("row_click_and_enter_navigate_to_detail: con clic en la fila", async () => {
    renderTable();

    await userEvent.click(within(rowOf("Av. Los Estudiantes")).getByText("8,70"));

    expect(screen.getByTestId("location")).toHaveTextContent(`/reportes/${ESTUDIANTES.id}`);
  });

  it("row_click_and_enter_navigate_to_detail: con el teclado", async () => {
    renderTable();

    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Av. Los Estudiantes" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");

    expect(screen.getByTestId("location")).toHaveTextContent(`/reportes/${ESTUDIANTES.id}`);
  });
});
