import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import { renderScreen } from "../../test/render";
import type { Round, RoundProgress } from "./api";
import { CLOSED_ROUND, OPEN_PROGRESS, OPEN_ROUND } from "./fixtures";
import { RoundsPanel } from "./RoundsPanel";

const ROUNDS = "/api/v1/admin/evaluation-rounds";

type State = { rounds: Round[]; progress: RoundProgress };

function renderPanel(state: State, post: (path: string) => Promise<unknown> = async () => ({})) {
  const get = vi.fn(async (path: string): Promise<unknown> => {
    if (path === ROUNDS) {
      return { items: state.rounds, limit: 20, offset: 0 };
    }
    if (path === `${ROUNDS}/${state.progress.id}`) {
      return state.progress;
    }
    throw new Error(`Ruta no prevista: ${path}`);
  });
  const postSpy = vi.fn(post);
  renderScreen(<RoundsPanel />, { api: { get: get as never, post: postSpy as never } });
  return { get, post: postSpy };
}

describe("rondas de evaluación", () => {
  it("la ronda abierta muestra el avance por zona y evaluador", async () => {
    renderPanel({ rounds: [OPEN_ROUND, CLOSED_ROUND], progress: OPEN_PROGRESS });

    const progress = await screen.findByRole("table", { name: "Avance de la ronda «Piloto 2»" });
    const rows = within(progress).getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      "CentroAlta concentración10Evaluador 1",
      "ObonucoBaja concentración6Ningún evaluador todavía",
    ]);
    // Con una ronda abierta no se ofrece abrir otra.
    expect(screen.queryByRole("button", { name: "Abrir ronda" })).toBeNull();
    const history = screen.getByRole("table", { name: "Rondas anteriores" });
    expect(within(history).getByText("Piloto 1")).toBeInTheDocument();
    expect(within(history).getByText("Cerrada")).toBeInTheDocument();
  });

  it("sin ronda abierta ofrece abrir una", async () => {
    renderPanel({ rounds: [CLOSED_ROUND], progress: OPEN_PROGRESS });

    expect(await screen.findByRole("button", { name: "Abrir ronda" })).toBeInTheDocument();
  });

  it("sin ninguna ronda lo dice y ofrece abrir la primera", async () => {
    renderPanel({ rounds: [], progress: OPEN_PROGRESS });

    expect(await screen.findByText("Aún no hay rondas")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir ronda" })).toBeInTheDocument();
  });

  it("cerrar pide confirmación y no envía dos veces", async () => {
    let resolveClose: (value: unknown) => void = () => {};
    const { post } = renderPanel(
      { rounds: [OPEN_ROUND], progress: OPEN_PROGRESS },
      () =>
        new Promise((resolve) => {
          resolveClose = resolve;
        }),
    );

    await userEvent.click(await screen.findByRole("button", { name: "Cerrar ronda" }));
    expect(post).not.toHaveBeenCalled();
    const dialog = screen.getByRole("group", { name: "Confirmar el cierre" });
    expect(dialog).toHaveTextContent("Ya no se aceptarán órdenes");

    await userEvent.click(within(dialog).getByRole("button", { name: "Sí, cerrar la ronda" }));
    expect(within(dialog).getByRole("button", { name: "Cerrando…" })).toBeDisabled();
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith(`${ROUNDS}/${OPEN_ROUND.id}/close`);
    resolveClose({ ...OPEN_ROUND, status: "cerrada" });
  });

  it("cancelar el cierre no cierra la ronda", async () => {
    const { post } = renderPanel({ rounds: [OPEN_ROUND], progress: OPEN_PROGRESS });

    await userEvent.click(await screen.findByRole("button", { name: "Cerrar ronda" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(post).not.toHaveBeenCalled();
    expect(screen.queryByRole("group", { name: "Confirmar el cierre" })).toBeNull();
  });

  it("si cerrar falla, muestra el mensaje", async () => {
    renderPanel({ rounds: [OPEN_ROUND], progress: OPEN_PROGRESS }, async () => {
      throw new ApiError(409, "EVALUATION_ROUND_CLOSED", "La ronda de evaluación ya está cerrada.");
    });

    await userEvent.click(await screen.findByRole("button", { name: "Cerrar ronda" }));
    await userEvent.click(screen.getByRole("button", { name: "Sí, cerrar la ronda" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La ronda de evaluación ya está cerrada.",
    );
  });

  it("un error al cargar las rondas permite reintentar", async () => {
    const get = vi.fn(async () => {
      throw new ApiError(500, "INTERNAL_ERROR", "Falló");
    });
    renderScreen(<RoundsPanel />, { api: { get: get as never } });

    expect(await screen.findByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});
