import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EmptyView, ErrorView, LoadingView } from "./StateViews";

describe("vistas de estado", () => {
  it("la carga se anuncia a los lectores de pantalla", () => {
    render(<LoadingView />);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando…");
  });

  it("el estado vacío muestra título y detalle", () => {
    render(<EmptyView title="Sin reportes" detail="Aún no hay reportes evaluados." />);
    expect(screen.getByText("Sin reportes")).toBeInTheDocument();
    expect(screen.getByText("Aún no hay reportes evaluados.")).toBeInTheDocument();
  });

  it("el error muestra el mensaje y permite reintentar", async () => {
    const onRetry = vi.fn();
    render(<ErrorView message="No se pudo cargar." onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo cargar.");
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
