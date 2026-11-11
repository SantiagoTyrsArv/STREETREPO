import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError, type QueryParams } from "../../api/client";
import { renderScreen } from "../../test/render";
import type { RankingItem } from "./api";
import { PrioritizationPage } from "./PrioritizationPage";
import { ESTUDIANTES, OBONUCO } from "./fixtures";

// Leaflet necesita un navegador real: aquí se sustituye el mapa y se prueba aparte su leyenda.
vi.mock("./HeatMap", () => ({
  HeatMap: ({ points }: { points: unknown[] }) => (
    <div data-testid="heat-map">{points.length} puntos</div>
  ),
}));

type Ranking = { items: RankingItem[]; total: number };

function makeApi(ranking: () => Ranking | Promise<Ranking>) {
  const get = vi.fn(async (path: string, query?: QueryParams): Promise<unknown> => {
    switch (path) {
      case "/api/v1/admin/summary":
        return { active: 12, evaluated: 7, prioritized: 3, repaired: 5 };
      case "/api/v1/admin/heatmap":
        return { points: [{ lat: 1.21, lon: -77.28, u: 8.7 }] };
      case "/api/v1/admin/weights":
        return { id: 4, w_severity: 0.5, w_flow: 0.3, w_proximity: 0.2, is_current: true };
      case "/api/v1/admin/ranking": {
        const { items, total } = await ranking();
        return { items, total, limit: query?.limit, offset: query?.offset };
      }
      default:
        throw new Error(`Ruta no prevista: ${path}`);
    }
  });
  return get;
}

function rankingCalls(get: ReturnType<typeof makeApi>): QueryParams[] {
  return get.mock.calls
    .filter(([path]) => path === "/api/v1/admin/ranking")
    .map(([, query]) => query ?? {});
}

function renderPage(get: ReturnType<typeof makeApi>) {
  renderScreen(<PrioritizationPage />, { api: { get: get as never } });
}

describe("pantalla Priorización", () => {
  it("muestra los indicadores, la fórmula con los pesos vigentes y el ranking", async () => {
    renderPage(makeApi(() => ({ items: [ESTUDIANTES, OBONUCO], total: 2 })));

    expect(
      await screen.findByRole("heading", { name: "Priorización de reportes" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Av. Los Estudiantes" })).toBeInTheDocument();
    expect(
      await screen.findByText("Ranking por urgencia U = 0,5·S + 0,3·F + 0,2·P (pesos vigentes)"),
    ).toBeInTheDocument();
    const summary = within(screen.getByRole("list", { name: "Reportes por estado" }));
    await waitFor(() =>
      expect(summary.getAllByRole("listitem").map((item) => item.textContent)).toEqual([
        "Activos12",
        "Evaluados7",
        "Priorizados3",
        "Reparados5",
      ]),
    );
    expect(await screen.findByTestId("heat-map")).toHaveTextContent("1 puntos");
  });

  it("empty_state_when_no_reports: texto del diseño y mapa sin error", async () => {
    renderPage(makeApi(() => ({ items: [], total: 0 })));

    expect(await screen.findByText("Aún no hay reportes")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Cuando los ciudadanos envíen reportes aparecerán aquí, ordenados por urgencia.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId("heat-map")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("error_state_with_retry: «Reintentar» vuelve a pedir el ranking", async () => {
    let fail = true;
    const get = makeApi(() => {
      if (fail) {
        throw new ApiError(500, "INTERNAL_ERROR", "Error interno");
      }
      return { items: [ESTUDIANTES], total: 1 };
    });
    renderPage(get);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No pudimos cargar el ranking");
    expect(alert).toHaveTextContent(
      "Hubo un problema al consultar el servidor. Inténtalo de nuevo.",
    );

    fail = false;
    await userEvent.click(within(alert).getByRole("button", { name: "Reintentar" }));

    expect(await screen.findByRole("link", { name: "Av. Los Estudiantes" })).toBeInTheDocument();
    expect(rankingCalls(get)).toHaveLength(2);
  });

  it("status_filter_requests_selected_statuses: por defecto los activos", async () => {
    const get = makeApi(() => ({ items: [ESTUDIANTES], total: 1 }));
    renderPage(get);
    await screen.findByRole("link", { name: "Av. Los Estudiantes" });
    // Sin `status`, el servidor devuelve los activos (decisión 13).
    expect(rankingCalls(get)[0]).toEqual({ status: [], limit: 20, offset: 0 });

    await userEvent.selectOptions(screen.getByLabelText("Estado"), "Estado: reparados");

    await waitFor(() =>
      expect(rankingCalls(get).at(-1)).toEqual({ status: ["reparado"], limit: 20, offset: 0 }),
    );
  });

  it("un filtro sin resultados lo dice sin el texto de «aún no hay reportes»", async () => {
    renderPage(makeApi(() => ({ items: [], total: 0 })));
    await screen.findByText("Aún no hay reportes");

    await userEvent.selectOptions(screen.getByLabelText("Estado"), "Estado: reparados");

    expect(await screen.findByText("No hay reportes en este estado")).toBeInTheDocument();
  });

  it("pagination_requests_next_offset: avanza y vuelve de página", async () => {
    const get = makeApi(() => ({ items: [ESTUDIANTES], total: 45 }));
    renderPage(get);
    await screen.findByRole("link", { name: "Av. Los Estudiantes" });
    expect(screen.getByText("1–20 de 45")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));

    await waitFor(() => expect(rankingCalls(get).at(-1)).toMatchObject({ offset: 20 }));
    expect(await screen.findByText("21–40 de 45")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));

    expect(await screen.findByText("41–45 de 45")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
  });

  it("cambiar el filtro vuelve a la primera página", async () => {
    const get = makeApi(() => ({ items: [ESTUDIANTES], total: 45 }));
    renderPage(get);
    await screen.findByRole("link", { name: "Av. Los Estudiantes" });
    await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    await screen.findByText("21–40 de 45");

    await userEvent.selectOptions(screen.getByLabelText("Estado"), "Estado: evaluados");

    await waitFor(() =>
      expect(rankingCalls(get).at(-1)).toEqual({ status: ["evaluado"], limit: 20, offset: 0 }),
    );
  });
});
