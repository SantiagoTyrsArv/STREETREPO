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

  it("el estado vacío puede llevar un signo decorativo que no se lee en voz alta", () => {
    render(<EmptyView mark="0" title="Aún no hay reportes" />);
    expect(screen.getByText("0")).toHaveAttribute("aria-hidden", "true");
  });

  it("el error con título muestra qué falló y el detalle", () => {
    render(
      <ErrorView title="No pudimos cargar el ranking" message="Sin conexión." onRetry={() => {}} />,
    );
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("No pudimos cargar el ranking");
    expect(alert).toHaveTextContent("Sin conexión.");
  });
});
