import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CURRENT_VERSION } from "./fixtures";
import { WeightsForm } from "./WeightsForm";

const SAVE = "Guardar y recalcular puntajes";

function renderForm(saving = false) {
  const onSave = vi.fn();
  render(<WeightsForm current={CURRENT_VERSION} saving={saving} onSave={onSave} />);
  return onSave;
}

function field(name: RegExp) {
  return screen.getByRole("textbox", { name });
}

async function setWeights(w1: string, w2: string, w3: string) {
  for (const [name, value] of [
    [/Severidad/, w1],
    [/Flujo vehicular/, w2],
    [/Proximidad/, w3],
  ] as const) {
    await userEvent.clear(field(name));
    await userEvent.type(field(name), value);
  }
}

describe("formulario de pesos", () => {
  it("parte de la versión vigente y no guarda sin cambios", () => {
    renderForm();

    expect(field(/Severidad/)).toHaveValue("0,50");
    expect(field(/Flujo vehicular/)).toHaveValue("0,30");
    expect(field(/Proximidad/)).toHaveValue("0,20");
    expect(screen.getByText("Σ = 1,00")).toBeInTheDocument();
    expect(screen.getByText("Los pesos suman 1,00")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: SAVE })).toBeDisabled();
  });

  it("save_disabled_when_sum_not_one: 0,50 + 0,30 + 0,19 no se puede guardar", async () => {
    const onSave = renderForm();

    await setWeights("0,50", "0,30", "0,19");

    expect(screen.getByText("Σ = 0,99")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Los pesos suman 0,99. Deben sumar exactamente 1,00.",
    );
    expect(screen.getByRole("button", { name: SAVE })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: SAVE }));
    expect(onSave).not.toHaveBeenCalled();
  });

  it("accepts_comma_decimals: 0,6 + 0,3 + 0,1 se guarda con punto y dos decimales", async () => {
    const onSave = renderForm();

    await setWeights("0,6", "0,3", "0,1");

    expect(screen.getByText("Σ = 1,00")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: SAVE }));
    expect(onSave).toHaveBeenCalledWith({
      w_severity: "0.60",
      w_flow: "0.30",
      w_proximity: "0.10",
    });
  });

  it("rejects_three_decimals_with_message: explica por qué no se puede guardar", async () => {
    renderForm();

    await userEvent.clear(field(/Severidad/));
    await userEvent.type(field(/Severidad/), "0,505");

    expect(field(/Severidad/)).toBeInvalid();
    expect(
      screen.getByText("Escribe un número entre 0 y 1 con máximo dos decimales, por ejemplo 0,25."),
    ).toBeInTheDocument();
    expect(screen.getByText("Σ = —")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: SAVE })).toBeDisabled();
  });

  it("el deslizador y el campo muestran el mismo valor", () => {
    renderForm();

    fireEvent.change(screen.getByRole("slider", { name: /Severidad/ }), {
      target: { value: "65" },
    });

    expect(field(/Severidad/)).toHaveValue("0,65");
    expect(screen.getByText("Σ = 1,15")).toBeInTheDocument();
  });

  it("«Restaurar» vuelve a los valores iniciales del modelo", async () => {
    renderForm();
    await setWeights("0,6", "0,3", "0,1");

    await userEvent.click(screen.getByRole("button", { name: "Restaurar 0,5 / 0,3 / 0,2" }));

    expect(field(/Severidad/)).toHaveValue("0,50");
    expect(field(/Proximidad/)).toHaveValue("0,20");
  });

  it("mientras guarda no permite el envío doble", () => {
    renderForm(true);

    expect(screen.getByRole("button", { name: "Guardando…" })).toBeDisabled();
  });
});
