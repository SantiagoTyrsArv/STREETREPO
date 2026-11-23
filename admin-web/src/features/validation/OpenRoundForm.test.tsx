import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import { renderScreen } from "../../test/render";
import { OpenRoundForm } from "./OpenRoundForm";

type Post = (path: string, body?: unknown) => Promise<unknown>;

function renderForm(post: Post) {
  const spy = vi.fn(post);
  renderScreen(<OpenRoundForm />, { api: { post: spy as never } });
  return spy;
}

async function fill(name: string, size: string) {
  await userEvent.type(screen.getByLabelText("Nombre de la ronda"), name);
  const sample = screen.getByLabelText(/Reportes por zona/);
  await userEvent.clear(sample);
  await userEvent.type(sample, size);
  await userEvent.click(screen.getByRole("button", { name: "Abrir ronda" }));
}

describe("abrir una ronda", () => {
  it("envía el nombre y el tamaño de muestra", async () => {
    const post = renderForm(async () => ({ id: "r-3" }));

    await fill("  Piloto 3 ", "8");

    expect(post).toHaveBeenCalledWith("/api/v1/admin/evaluation-rounds", {
      name: "Piloto 3",
      sample_size: 8,
    });
  });

  it.each(["0", "101", "abc"])("no envía un tamaño fuera de 1 a 100 (%s)", async (size) => {
    const post = renderForm(async () => ({ id: "r-3" }));

    await fill("Piloto 3", size);

    expect(post).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "El tamaño de la muestra debe ser un número entero de 1 a 100.",
    );
  });

  it("una zona con pocos reportes muestra cuál es y cuántos tiene", async () => {
    renderForm(async () => {
      throw new ApiError(
        422,
        "EVALUATION_ZONE_TOO_SMALL",
        "La zona «Obonuco» tiene 3 reportes activos y se necesitan al menos 5.",
        { zone: "Obonuco", reports: 3, minimum: 5 },
      );
    });

    await fill("Piloto 3", "8");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La zona «Obonuco» tiene 3 reportes activos y se necesitan al menos 5.",
    );
    // Conserva lo escrito para corregir y reintentar (guía 10.3).
    expect(screen.getByLabelText("Nombre de la ronda")).toHaveValue("Piloto 3");
  });

  it("otra ronda abierta muestra el mensaje del servidor", async () => {
    renderForm(async () => {
      throw new ApiError(
        409,
        "EVALUATION_ROUND_ALREADY_OPEN",
        "Ya hay una ronda de evaluación abierta. Ciérrala antes de abrir otra.",
      );
    });

    await fill("Piloto 3", "8");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ya hay una ronda de evaluación abierta.",
    );
  });

  it("no envía dos veces mientras espera la respuesta", async () => {
    const post = renderForm(() => new Promise(() => {}));

    await fill("Piloto 3", "8");

    expect(screen.getByRole("button", { name: "Abriendo…" })).toBeDisabled();
    expect(post).toHaveBeenCalledTimes(1);
  });
});
