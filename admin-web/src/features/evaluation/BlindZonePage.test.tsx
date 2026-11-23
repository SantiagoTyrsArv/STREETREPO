import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import { renderScreen } from "../../test/render";
import { BlindZonePage } from "./BlindZonePage";
import { CENTRO_CARDS, CURRENT_ROUND } from "./fixtures";
import { draftKey } from "./useDraftOrder";

vi.mock("./BlindMap", () => ({ BlindMap: () => <p>Minimapa</p> }));

const CURRENT = "/api/v1/evaluation/current";

type Put = (path: string, body: unknown) => Promise<unknown>;

function renderZone(
  put: Put = async () => ({ zone_id: 1, submitted: true }),
  cards = CENTRO_CARDS,
) {
  const get = vi.fn(async (path: string): Promise<unknown> => {
    if (path === CURRENT) {
      return CURRENT_ROUND;
    }
    if (path === `${CURRENT}/zones/1`) {
      return cards;
    }
    throw new Error(`Ruta no prevista: ${path}`);
  });
  const putSpy = vi.fn(put);
  renderScreen(<BlindZonePage />, {
    api: {
      get: get as never,
      put: putSpy as never,
      getBlob: (() => new Promise(() => {})) as never,
    },
    path: "/evaluacion/zonas/1",
    route: "/evaluacion/zonas/:zoneId",
  });
  return putSpy;
}

async function roads(): Promise<string[]> {
  const list = await screen.findByRole("list", {
    name: "Reportes de la zona, del más urgente al menos urgente",
  });
  return within(list)
    .getAllByRole("listitem")
    .map((item) => within(item).getByRole("heading").textContent ?? "");
}

beforeEach(() => sessionStorage.clear());

describe("vista a ciegas de una zona", () => {
  it("muestra las tarjetas en el orden del servidor", async () => {
    renderZone();

    expect(await screen.findByRole("heading", { name: "Zona Centro" })).toBeInTheDocument();
    expect(screen.getByText("Ronda «Piloto 1» · 3 reportes")).toBeInTheDocument();
    expect(await roads()).toEqual(["Carrera 27", "Calle 18", "Vía sin nombre"]);
    expect(screen.getByText("Hueco profundo frente al colegio")).toBeInTheDocument();
  });

  it("nunca muestra datos del motor", async () => {
    renderZone();
    await roads();

    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/\bU\b|puntaje|urgencia|confirmaci|orden del motor|prioridad/i);
  });

  it("subir y bajar cambian el orden y lo anuncian", async () => {
    renderZone();
    await roads();

    await userEvent.click(screen.getByRole("button", { name: "Subir Calle 18" }));

    expect(await roads()).toEqual(["Calle 18", "Carrera 27", "Vía sin nombre"]);
    expect(screen.getByRole("status", { name: "Cambios en el orden" })).toHaveTextContent(
      "Calle 18, ahora en la posición 1 de 3",
    );
    expect(screen.getByRole("button", { name: "Subir Calle 18" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Bajar Carrera 27" }));

    expect(await roads()).toEqual(["Calle 18", "Vía sin nombre", "Carrera 27"]);
    expect(screen.getByRole("button", { name: "Bajar Carrera 27" })).toBeDisabled();
  });

  it("recargar conserva el orden que se estaba armando", async () => {
    sessionStorage.setItem(draftKey("r-1", 1), JSON.stringify(["c", "a", "b"]));

    renderZone();

    expect(await roads()).toEqual(["Vía sin nombre", "Carrera 27", "Calle 18"]);
  });

  it("enviar pide confirmación y manda el orden visible", async () => {
    const put = renderZone();
    await roads();
    await userEvent.click(screen.getByRole("button", { name: "Bajar Carrera 27" }));

    await userEvent.click(screen.getByRole("button", { name: "Enviar este orden" }));
    expect(put).not.toHaveBeenCalled();
    const confirm = screen.getByRole("group", { name: "Confirmar el envío" });
    expect(confirm).toHaveTextContent("No podrás cambiarlo");
    await userEvent.click(within(confirm).getByRole("button", { name: "Sí, enviar" }));

    expect(put).toHaveBeenCalledWith(`${CURRENT}/zones/1/order`, { report_ids: ["b", "a", "c"] });
    expect(await screen.findByTestId("location")).toHaveTextContent("/evaluacion");
    expect(sessionStorage.getItem(draftKey("r-1", 1))).toBeNull();
  });

  it("si ya se envió, lo dice", async () => {
    renderZone(async () => {
      throw new ApiError(409, "EVALUATION_ORDER_ALREADY_SUBMITTED", "Ya enviaste el orden.");
    });
    await roads();

    await userEvent.click(screen.getByRole("button", { name: "Enviar este orden" }));
    await userEvent.click(screen.getByRole("button", { name: "Sí, enviar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ya enviaste esta zona.");
  });

  it("sin conexión conserva el borrador y deja reintentar", async () => {
    let calls = 0;
    const put = renderZone(async () => {
      calls += 1;
      if (calls === 1) {
        throw new ApiError(
          0,
          "NETWORK_ERROR",
          "No hay conexión con el servidor. Revisa tu red e intenta de nuevo.",
        );
      }
      return { zone_id: 1, submitted: true };
    });
    await roads();
    await userEvent.click(screen.getByRole("button", { name: "Bajar Carrera 27" }));
    await userEvent.click(screen.getByRole("button", { name: "Enviar este orden" }));
    await userEvent.click(screen.getByRole("button", { name: "Sí, enviar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No hay conexión con el servidor.");
    expect(await roads()).toEqual(["Calle 18", "Carrera 27", "Vía sin nombre"]);

    await userEvent.click(screen.getByRole("button", { name: "Sí, enviar" }));

    expect(put).toHaveBeenCalledTimes(2);
    expect(put).toHaveBeenLastCalledWith(`${CURRENT}/zones/1/order`, {
      report_ids: ["b", "a", "c"],
    });
  });

  it("una zona ya enviada no deja ordenar", async () => {
    renderZone(undefined, { ...CENTRO_CARDS, submitted: true });

    expect(await screen.findByText("Ya enviaste el orden de esta zona.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enviar este orden" })).toBeNull();
  });

  it("Ver en el mapa abre el panel lateral con el minimapa", async () => {
    renderZone();
    await roads();

    await userEvent.click(screen.getByRole("button", { name: "Ver en el mapa Carrera 27" }));

    const panel = screen.getByRole("complementary", { name: "Carrera 27" });
    expect(within(panel).getByText("Minimapa")).toBeInTheDocument();
    expect(within(panel).getByText("I. E. M. Ciudad de Pasto · Escuela")).toBeInTheDocument();

    await userEvent.click(within(panel).getByRole("button", { name: "Cerrar el mapa" }));

    expect(screen.queryByRole("complementary", { name: "Carrera 27" })).toBeNull();
  });
});
