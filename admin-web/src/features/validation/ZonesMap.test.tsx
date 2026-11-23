import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import { renderScreen } from "../../test/render";
import { ZONES } from "./fixtures";
import { ZonesMap } from "./ZonesMap";

// Leaflet no dibuja en jsdom; el mapa tiene su propia prueba manual.
vi.mock("./ZonePolygons", () => ({ ZonePolygons: () => null }));

function renderZones(get: () => Promise<unknown>) {
  const spy = vi.fn(get);
  renderScreen(<ZonesMap />, { api: { get: spy as never } });
  return spy;
}

describe("zonas de validación", () => {
  it("muestra cada zona con su concentración en texto y sus reportes", async () => {
    renderZones(async () => ({ items: ZONES }));

    const table = await screen.findByRole("table", { name: "Zonas del estudio" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      "CentroAlta concentración1418",
      "ObonucoBaja concentración67",
    ]);
    const legend = screen.getByRole("group", { name: "Concentración de reportes" });
    expect(legend).toHaveTextContent("Alta concentración");
    expect(legend).toHaveTextContent("Baja concentración");
    expect(
      screen.getByRole("region", { name: "Mapa de las zonas del estudio" }),
    ).toBeInTheDocument();
  });

  it("mientras carga muestra el estado de carga", () => {
    renderZones(() => new Promise(() => {}));

    expect(screen.getByRole("status")).toHaveTextContent("Cargando las zonas…");
  });

  it("sin zonas explica cómo cargarlas", async () => {
    renderZones(async () => ({ items: [] }));

    expect(await screen.findByText("Aún no hay zonas")).toBeInTheDocument();
    expect(screen.getByText(/cárgalas con zones-import/)).toBeInTheDocument();
  });

  it("un error permite reintentar", async () => {
    let calls = 0;
    const get = renderZones(async () => {
      calls += 1;
      if (calls === 1) {
        throw new ApiError(500, "INTERNAL_ERROR", "Falló");
      }
      return { items: ZONES };
    });

    await userEvent.click(await screen.findByRole("button", { name: "Reintentar" }));

    expect(await screen.findByRole("table", { name: "Zonas del estudio" })).toBeInTheDocument();
    expect(get).toHaveBeenCalledTimes(2);
  });
});
