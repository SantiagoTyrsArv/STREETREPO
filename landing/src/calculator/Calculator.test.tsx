import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Calculator } from "./Calculator";

describe("Calculator", () => {
  it("empieza con un caso de la tabla de la guía y muestra 8,70", () => {
    render(<Calculator />);
    expect(within(screen.getByRole("status")).getByText("8,70")).toBeInTheDocument();
  });

  it("recalcula al cambiar severidad, vía y distancia", () => {
    render(<Calculator />);
    fireEvent.click(screen.getByRole("radio", { name: "Media" }));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "principal" } });
    fireEvent.change(screen.getByRole("slider"), { target: { value: "100" } });
    expect(within(screen.getByRole("status")).getByText("8,00")).toBeInTheDocument();
  });

  it("sin vía marca «Revisar vía»", () => {
    render(<Calculator />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "sin-via" } });
    expect(screen.getByText("Revisar vía")).toBeInTheDocument();
  });

  it("usa controles nativos con nombre, que el navegador maneja con teclado", () => {
    render(<Calculator />);
    const radios = screen.getAllByRole("radio") as HTMLInputElement[];
    expect(radios.map((r) => r.labels?.[0]?.textContent)).toEqual(["Baja", "Media", "Alta"]);
    expect(new Set(radios.map((r) => r.name)).size).toBe(1);
    expect(screen.getByRole("combobox", { name: /vía/i })).toBeInstanceOf(HTMLSelectElement);
    const slider = screen.getByRole("slider", { name: /distancia/i }) as HTMLInputElement;
    expect(slider.type).toBe("range");
    expect(slider).toHaveAttribute("aria-valuetext", "180 m");
  });

  it("ya no es un capítulo: no tiene sección ni ancla propias", () => {
    const { container } = render(<Calculator titleId="calc-titulo" />);
    expect(container.querySelector("section")).toBeNull();
    expect(container.querySelector("#prueba")).toBeNull();
    expect(screen.getByRole("heading", { name: "Calcula una urgencia." })).toHaveAttribute(
      "id",
      "calc-titulo",
    );
  });

  it("solo anuncia la urgencia (y la marca de vía), no el desglose ni la nota", () => {
    render(<Calculator />);
    const status = screen.getByRole("status");
    expect(status.textContent).toContain("8,70");
    expect(status.textContent).not.toContain("pesos por defecto");
    expect(status.textContent).not.toContain("=");
  });
});
