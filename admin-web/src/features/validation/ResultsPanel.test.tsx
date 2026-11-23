import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderScreen } from "../../test/render";
import type { Round, RoundResults } from "./api";
import { CLOSED_ROUND, OPEN_ROUND, RESULTS } from "./fixtures";
import { ResultsPanel } from "./ResultsPanel";

const ROUNDS = "/api/v1/admin/evaluation-rounds";

const COMPUTED: RoundResults = {
  ...RESULTS,
  zones: [
    RESULTS.zones[0]!,
    {
      ...RESULTS.zones[0]!,
      zone_id: 2,
      name: "Obonuco",
      concentration: "baja",
      agreement: {
        ...RESULTS.zones[0]!.agreement!,
        n_evaluators: 1,
        kendall_w: null,
        within_one_pct: 62.5,
      },
    },
  ],
  between: {
    computable: true,
    test: "mann_whitney",
    statistic: 4.5,
    p_value: 0.0312,
    significant: true,
    reason: null,
  },
};

function renderPanel(rounds: Round[], results: RoundResults = RESULTS) {
  const get = vi.fn(async (path: string): Promise<unknown> => {
    if (path === ROUNDS) {
      return { items: rounds, limit: 20, offset: 0 };
    }
    if (path === `${ROUNDS}/${CLOSED_ROUND.id}/results`) {
      return results;
    }
    throw new Error(`Ruta no prevista: ${path}`);
  });
  const getFile = vi.fn(async () => ({
    blob: new Blob(["id_reporte\n"]),
    filename: "ronda-piloto-1-ficha.csv",
  }));
  renderScreen(<ResultsPanel />, { api: { get: get as never, getFile: getFile as never } });
  return { get, getFile };
}

describe("resultados de la ronda", () => {
  it("muestra las cifras, las métricas por zona con coma decimal y la nota fija", async () => {
    renderPanel([OPEN_ROUND, CLOSED_ROUND], COMPUTED);

    const figures = await screen.findByRole("region", { name: "Cifras de la ronda «Piloto 1»" });
    expect(figures).toHaveTextContent("80 %");
    expect(figures).toHaveTextContent("Coincidencia ±1 · Centro (alta concentración)");
    expect(figures).toHaveTextContent("p = 0,031");

    const centro = screen.getByRole("region", { name: "Acuerdo en Centro" });
    expect(centro).toHaveTextContent("rho de Spearman0,81p = 0,021");
    expect(centro).toHaveTextContent("tau-b de Kendall0,60p = 0,045");
    expect(centro).toHaveTextContent("W de Kendall0,88p = 0,072");
    expect(within(centro).getByText("Evaluador 2")).toBeInTheDocument();

    const obonuco = screen.getByRole("region", { name: "Acuerdo en Obonuco" });
    expect(obonuco).toHaveTextContent("Se necesitan al menos 2 evaluadores");
    expect(obonuco).toHaveTextContent("62,5 %");

    const between = screen.getByRole("region", { name: "Prueba entre zonas" });
    expect(between).toHaveTextContent("U de Mann-Whitney");
    expect(between).toHaveTextContent("Estadístico4,50");
    expect(between).toHaveTextContent("Diferencia significativa con α = 0,05: Sí");

    expect(
      screen.getByText(
        "Estos valores describen la ronda; la interpretación de las hipótesis se hace en la tesis.",
      ),
    ).toBeInTheDocument();
  });

  it("el ranking comparado muestra motor, panel y la diferencia", async () => {
    renderPanel([CLOSED_ROUND]);

    const table = await screen.findByRole("table", { name: "Ranking comparado · zona Centro" });
    const rows = within(table)
      .getAllByRole("row")
      .slice(1)
      .map((row) => row.textContent);
    expect(rows).toEqual([
      "Carrera 2711,5▼ 0,5",
      "Calle 1824▼ 2",
      "Vía sin nombre31,5▲ 1,5",
      "Calle 2043▲ 1",
      "Carrera 2455Igual",
    ]);
  });

  it("una prueba que no se pudo calcular dice por qué, y una zona sin órdenes también", async () => {
    renderPanel([CLOSED_ROUND]);

    const between = await screen.findByRole("region", { name: "Prueba entre zonas" });
    expect(between).toHaveTextContent(
      "No se calculó: Se necesita al menos una zona de alta y una de baja concentración con órdenes",
    );
    expect(screen.getByRole("region", { name: "Acuerdo en Obonuco" })).toHaveTextContent(
      "Ningún evaluador envió el orden de esta zona.",
    );
  });

  it("la tabla de deduplicación da reportes, confirmaciones y avisos por zona", async () => {
    renderPanel([CLOSED_ROUND]);

    const table = await screen.findByRole("table", { name: "Deduplicación por zona" });
    const rows = within(table)
      .getAllByRole("row")
      .slice(1)
      .map((row) => row.textContent);
    expect(rows).toEqual(["Centro18697421", "Obonuco7690421"]);
  });

  it("con solo una ronda abierta no pide resultados", async () => {
    const { get } = renderPanel([OPEN_ROUND]);

    expect(
      await screen.findByText("Los resultados se muestran al cerrar la ronda."),
    ).toBeInTheDocument();
    expect(get).not.toHaveBeenCalledWith(expect.stringContaining("/results"));
  });

  it("sin rondas lo dice", async () => {
    renderPanel([]);

    expect(await screen.findByText("Aún no hay rondas cerradas")).toBeInTheDocument();
  });

  describe("descargas", () => {
    const clicked: string[] = [];
    beforeEach(() => {
      clicked.length = 0;
      vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
        this: HTMLAnchorElement,
      ) {
        clicked.push(this.download);
      });
      URL.createObjectURL = vi.fn(() => "blob:ficha");
      URL.revokeObjectURL = vi.fn();
    });
    afterEach(() => vi.restoreAllMocks());

    it("descarga la ficha con el nombre que da el servidor", async () => {
      const { getFile } = renderPanel([CLOSED_ROUND]);

      await userEvent.click(await screen.findByRole("button", { name: "Exportar ficha (CSV)" }));

      expect(getFile).toHaveBeenCalledWith(`${ROUNDS}/${CLOSED_ROUND.id}/export/ficha.csv`);
      expect(clicked).toEqual(["ronda-piloto-1-ficha.csv"]);
      expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:ficha");
    });

    it.each([
      ["Resumen (CSV)", "resumen"],
      ["Reportes para revisión (CSV)", "reportes"],
      ["Avisos de duplicado (CSV)", "avisos"],
    ])("«%s» pide su archivo", async (label, kind) => {
      const { getFile } = renderPanel([CLOSED_ROUND]);

      await userEvent.click(await screen.findByRole("button", { name: label }));

      expect(getFile).toHaveBeenCalledWith(`${ROUNDS}/${CLOSED_ROUND.id}/export/${kind}.csv`);
    });
  });
});
