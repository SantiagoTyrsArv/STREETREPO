import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import { renderScreen } from "../../test/render";
import { CURRENT_ROUND } from "./fixtures";
import { MyEvaluationsPage } from "./MyEvaluationsPage";

function renderPage(get: () => Promise<unknown>) {
  const spy = vi.fn(get);
  renderScreen(<MyEvaluationsPage />, {
    api: { get: spy as never },
    path: "/evaluacion",
    route: "/evaluacion",
  });
  return spy;
}

describe("Mis evaluaciones", () => {
  it("lista las zonas de la ronda con su estado", async () => {
    renderPage(async () => CURRENT_ROUND);

    expect(await screen.findByText("Ronda «Piloto 1» · 1 de 2 zonas enviadas")).toBeInTheDocument();
    const list = screen.getByRole("list", { name: "Zonas por evaluar" });
    const items = within(list).getAllByRole("listitem");
    expect(within(items[0]!).getByText("Pendiente")).toBeInTheDocument();
    expect(within(items[1]!).getByText("Enviada")).toBeInTheDocument();
    expect(within(items[1]!).queryByRole("link")).toBeNull();

    await userEvent.click(within(items[0]!).getByRole("link", { name: "Ordenar la zona Centro" }));

    expect(screen.getByTestId("location")).toHaveTextContent("/evaluacion/zonas/1");
  });

  it("sin ronda abierta lo explica", async () => {
    renderPage(async () => {
      throw new ApiError(404, "EVALUATION_NO_OPEN_ROUND", "No hay una ronda abierta.");
    });

    expect(await screen.findByText("No hay una ronda de evaluación abierta")).toBeInTheDocument();
  });

  it("un error permite reintentar", async () => {
    let calls = 0;
    renderPage(async () => {
      calls += 1;
      if (calls === 1) {
        throw new ApiError(0, "NETWORK_ERROR", "No hay conexión con el servidor.");
      }
      return CURRENT_ROUND;
    });

    await userEvent.click(await screen.findByRole("button", { name: "Reintentar" }));

    expect(await screen.findByRole("list", { name: "Zonas por evaluar" })).toBeInTheDocument();
  });
});
