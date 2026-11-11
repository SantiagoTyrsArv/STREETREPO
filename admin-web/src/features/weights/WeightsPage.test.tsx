import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import { renderScreen } from "../../test/render";
import type { WeightVersion } from "./api";
import { CURRENT_VERSION, INITIAL_VERSION } from "./fixtures";
import { WeightsPage } from "./WeightsPage";

const SAVE = "Guardar y recalcular puntajes";

type Put = (path: string, body: unknown) => Promise<unknown>;

function renderPage(put: Put, current: () => WeightVersion = () => CURRENT_VERSION) {
  const get = vi.fn(async (path: string): Promise<unknown> => {
    if (path === "/api/v1/admin/weights") {
      return current();
    }
    if (path === "/api/v1/admin/weights/versions") {
      return { items: [current(), INITIAL_VERSION], limit: 20, offset: 0 };
    }
    throw new Error(`Ruta no prevista: ${path}`);
  });
  const putSpy = vi.fn(put);
  renderScreen(<WeightsPage />, { api: { get: get as never, put: putSpy as never } });
  return { get, put: putSpy };
}

async function changeWeights() {
  const severity = await screen.findByRole("textbox", { name: /Severidad/ });
  await userEvent.clear(severity);
  await userEvent.type(severity, "0,6");
  const proximity = screen.getByRole("textbox", { name: /Proximidad/ });
  await userEvent.clear(proximity);
  await userEvent.type(proximity, "0,1");
  await userEvent.click(screen.getByRole("button", { name: SAVE }));
}

describe("pantalla Pesos del modelo", () => {
  it("muestra el título, las reglas en solo lectura y los pesos vigentes", async () => {
    renderPage(async () => ({}));

    expect(
      await screen.findByRole("heading", { name: "Pesos del modelo de priorización" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("textbox", { name: /Severidad/ })).toHaveValue("0,50");
    const rules = within(screen.getByRole("region", { name: "Reglas de normalización (0 a 10)" }));
    expect(rules.getByText("Baja = 3 · Media = 6 · Alta = 10")).toBeInTheDocument();
    expect(rules.getByText(/primaria 10 · secundaria 7 · terciaria 5/)).toBeInTheDocument();
    expect(
      rules.getByText(/100 m o menos; decrece linealmente hasta 0 a 500 m/),
    ).toBeInTheDocument();
    expect(rules.queryByRole("textbox")).toBeNull();
  });

  it("save_sends_base_version_and_shows_recalculated_count", async () => {
    const saved = { ...CURRENT_VERSION, id: 5, w_severity: 0.6, w_proximity: 0.1 };
    let current = CURRENT_VERSION;
    const { put } = renderPage(
      async () => {
        current = saved;
        return { version: saved, recalculated_reports: 7 };
      },
      () => current,
    );

    await changeWeights();

    expect(put).toHaveBeenCalledWith("/api/v1/admin/weights", {
      base_version_id: 4,
      w_severity: "0.60",
      w_flow: "0.30",
      w_proximity: "0.10",
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Pesos guardados. Se recalcularon 7 reportes activos.",
    );
    // El formulario queda sobre la versión nueva.
    expect(await screen.findByRole("textbox", { name: /Severidad/ })).toHaveValue("0,60");
  });

  it("conflict_409_offers_reload_current_version", async () => {
    const other = { ...CURRENT_VERSION, id: 9, w_severity: 0.4, w_flow: 0.4 };
    let current = CURRENT_VERSION;
    renderPage(
      async () => {
        current = other;
        throw new ApiError(
          409,
          "WEIGHTS_VERSION_CONFLICT",
          "Otro administrador guardó pesos nuevos. Revisa la versión vigente e inténtalo de nuevo.",
          { current_version_id: 9 },
        );
      },
      () => current,
    );

    await changeWeights();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Otro administrador guardó pesos nuevos.");
    // Lo escrito sigue ahí hasta que la persona decide cargar la versión vigente.
    expect(screen.getByRole("textbox", { name: /Severidad/ })).toHaveValue("0,6");

    await userEvent.click(within(alert).getByRole("button", { name: "Cargar la versión vigente" }));

    await waitFor(() =>
      expect(screen.getByRole("textbox", { name: /Severidad/ })).toHaveValue("0,40"),
    );
    expect(screen.getByRole("textbox", { name: /Flujo vehicular/ })).toHaveValue("0,40");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("server_422_message_shown", async () => {
    renderPage(async () => {
      throw new ApiError(422, "INVALID_WEIGHTS", "Los pesos deben sumar exactamente 1,00.");
    });

    await changeWeights();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Los pesos deben sumar exactamente 1,00.");
    expect(within(alert).queryByRole("button")).toBeNull();
  });

  it("versions_list_marks_current: fecha, autor, pesos y cuál está vigente", async () => {
    renderPage(async () => ({}));

    const versions = within(
      await screen.findByRole("region", { name: "Versiones de configuración" }),
    );
    const items = await versions.findAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      "0,50 / 0,30 / 0,2013 oct, 4:05 p. m. · Ana FuncionariaVigente",
      "0,50 / 0,30 / 0,2012 oct, 10:00 a. m. · Configuración inicial",
    ]);
  });
});
