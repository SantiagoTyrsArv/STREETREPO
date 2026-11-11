import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import { renderScreen } from "../../test/render";
import type { AdminReport } from "./api";
import { EVALUATED_REPORT, NO_ROAD_REPORT, REPORT_ID } from "./fixtures";
import { ReportDetailPage } from "./ReportDetailPage";

// Leaflet necesita un navegador real.
vi.mock("./LocationMap", () => ({
  LocationMap: ({ lat, lon }: { lat: number; lon: number }) => (
    <div data-testid="location-map">
      {lat},{lon}
    </div>
  ),
}));

beforeEach(() => {
  // jsdom no implementa las URL de objeto que usa la foto.
  vi.stubGlobal(
    "URL",
    Object.assign(URL, { createObjectURL: () => "blob:foto", revokeObjectURL: () => {} }),
  );
});

function renderDetail(report: AdminReport | (() => Promise<AdminReport>)) {
  const get = vi.fn(async (path: string) => {
    expect(path).toBe(`/api/v1/admin/reports/${REPORT_ID}`);
    return typeof report === "function" ? report() : report;
  });
  const getBlob = vi.fn(async () => new Blob(["x"], { type: "image/jpeg" }));
  renderScreen(<ReportDetailPage />, {
    api: { get: get as never, getBlob },
    path: `/reportes/${REPORT_ID}`,
    route: "/reportes/:id",
  });
  return { get, getBlob };
}

function card(name: string) {
  return within(screen.getByRole("region", { name }));
}

describe("pantalla Detalle y estado", () => {
  it("muestra el encabezado, la evidencia y los datos de la vía", async () => {
    renderDetail(EVALUATED_REPORT);

    expect(
      await screen.findByRole("heading", { level: 1, name: "Av. Los Estudiantes" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Reportado el 12 oct por Camila Ortega · Severidad alta"),
    ).toBeInTheDocument();
    const location = card("Ubicación y vía");
    expect(location.getByText("Av. Los Estudiantes")).toBeInTheDocument();
    expect(location.getByText("secundaria")).toBeInTheDocument();
    expect(location.getByTestId("location-map")).toHaveTextContent("1.2136,-77.2811");
    expect(
      location.getByText("“Hueco profundo frente a la entrada del colegio.”"),
    ).toBeInTheDocument();
    expect(
      location.getByText("4 personas confirmaron este daño (no modifica el puntaje)"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver al ranking" })).toHaveAttribute(
      "href",
      "/priorizacion",
    );
  });

  it("shows_breakdown_from_api: factores, pesos y U tal como llegan, con coma", async () => {
    renderDetail(EVALUATED_REPORT);

    const breakdown = within(await screen.findByRole("region", { name: "Cálculo de prioridad" }));
    expect(breakdown.getByText("Pesos 0,5 / 0,3 / 0,2 · versión 3")).toBeInTheDocument();
    expect(breakdown.getByText("10,00 × 0,5")).toBeInTheDocument();
    expect(breakdown.getByText("7,00 × 0,3")).toBeInTheDocument();
    expect(breakdown.getByText("8,00 × 0,2")).toBeInTheDocument();
    expect(breakdown.getByText("8,70")).toBeInTheDocument();
    expect(breakdown.getByText("Severidad · alta")).toBeInTheDocument();
    expect(breakdown.getByText("Flujo · vía secundaria")).toBeInTheDocument();
    expect(breakdown.getByText("Proximidad · escuela a 180,0 m")).toBeInTheDocument();
    expect(breakdown.getByText("Calculado el 13 oct")).toBeInTheDocument();
    // El panel no multiplica ni suma: no aparece ningún producto parcial.
    expect(breakdown.queryByText(/=/)).toBeNull();
  });

  it("shows_no_road_and_no_service_texts: sin vía y sin servicio a 500 m", async () => {
    renderDetail(NO_ROAD_REPORT);

    const location = within(await screen.findByRole("region", { name: "Ubicación y vía" }));
    expect(location.getByText("Sin vía asociada")).toBeInTheDocument();
    expect(location.getByText("Revisar vía")).toBeInTheDocument();
    expect(location.getByText("Nadie ha confirmado este daño todavía")).toBeInTheDocument();
    const breakdown = card("Cálculo de prioridad");
    expect(breakdown.getByText("Flujo · sin vía asociada")).toBeInTheDocument();
    expect(
      breakdown.getByText("Proximidad · ningún servicio crítico a menos de 500 m"),
    ).toBeInTheDocument();
    expect(breakdown.getByText("3,60")).toBeInTheDocument();
  });

  it("shows_pending_evaluation: un reporte sin evaluación no rompe la pantalla", async () => {
    renderDetail({
      ...EVALUATED_REPORT,
      status: "registrado",
      allowed_next_statuses: [],
      evaluation: null,
      history: EVALUATED_REPORT.history.slice(0, 1),
    });

    const breakdown = within(await screen.findByRole("region", { name: "Cálculo de prioridad" }));
    expect(breakdown.getByText("Pendiente de evaluación")).toBeInTheDocument();
    expect(card("Cambiar estado").getByText(/no admite más cambios/)).toBeInTheDocument();
  });

  it("history_shows_system_for_null_author: transición, fecha y quién", async () => {
    renderDetail({
      ...EVALUATED_REPORT,
      history: [
        ...EVALUATED_REPORT.history,
        {
          previous_status: "evaluado",
          status: "priorizado",
          changed_at: "2026-10-14T14:30:00Z",
          note: "Se programa para la próxima jornada de bacheo.",
          changed_by_name: "Ana Funcionaria",
        },
      ],
    });

    const history = within(await screen.findByRole("region", { name: "Historial de estados" }));
    const items = history.getAllByRole("listitem").map((item) => item.textContent);
    expect(items).toEqual([
      "Registrado12 oct, 10:00 a. m. · Camila Ortega",
      "Registrado → Evaluado13 oct, 4:05 p. m. · Sistema",
      "Evaluado → Priorizado14 oct, 9:30 a. m. · Ana Funcionaria«Se programa para la próxima jornada de bacheo.»",
    ]);
  });

  it("photo_uses_auth_image: la foto se pide con la sesión", async () => {
    const { getBlob } = renderDetail(EVALUATED_REPORT);

    expect(await screen.findByRole("img", { name: "Foto del daño" })).toHaveAttribute(
      "src",
      "blob:foto",
    );
    expect(getBlob).toHaveBeenCalledWith(`/api/v1/reports/${REPORT_ID}/photo`);
  });

  it("un reporte que no existe lo dice y ofrece volver", async () => {
    renderDetail(async () => {
      throw new ApiError(404, "REPORT_NOT_FOUND", "El reporte no existe.");
    });

    expect(await screen.findByText("No encontramos este reporte")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver al ranking" })).toBeInTheDocument();
  });

  it("un fallo del servidor permite reintentar", async () => {
    renderDetail(async () => {
      throw new ApiError(500, "INTERNAL_ERROR", "Error interno");
    });

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No pudimos cargar el reporte");
    expect(within(alert).getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});
