import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../api/client";
import type { ReportStatus } from "../../api/types";
import { renderScreen } from "../../test/render";
import type { AdminReport } from "./api";
import { EVALUATED_REPORT, REPORT_ID } from "./fixtures";
import { StatusChangeForm } from "./StatusChangeForm";

const NOTE = "Se programa para la próxima jornada de bacheo.";

type Patch = (path: string, body: unknown) => Promise<AdminReport>;

function renderForm(
  allowed: ReportStatus[] = ["priorizado", "reparado"],
  patch: Patch = async () => ({ ...EVALUATED_REPORT, status: "priorizado" }),
) {
  const spy = vi.fn(patch);
  renderScreen(<StatusChangeForm reportId={REPORT_ID} allowedStatuses={allowed} />, {
    api: { patch: spy as never },
  });
  return spy;
}

describe("formulario de cambio de estado", () => {
  it("status_options_come_from_api: solo ofrece los estados permitidos", () => {
    renderForm(["priorizado", "reparado"]);

    expect(screen.getAllByRole("radio").map((radio) => radio.getAttribute("value"))).toEqual([
      "priorizado",
      "reparado",
    ]);
    expect(screen.getByRole("radio", { name: "Priorizado" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Evaluado" })).toBeNull();
  });

  it("final_status_shows_no_more_changes: un reporte reparado no se puede cambiar", () => {
    renderForm([]);

    expect(screen.getByText("Este reporte no admite más cambios de estado.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar cambio" })).toBeNull();
  });

  it("no guarda sin elegir un estado", async () => {
    const patch = renderForm();

    expect(screen.getByRole("button", { name: "Guardar cambio" })).toBeDisabled();
    await userEvent.click(screen.getByRole("radio", { name: "Reparado" }));
    expect(screen.getByRole("button", { name: "Guardar cambio" })).toBeEnabled();
    expect(patch).not.toHaveBeenCalled();
  });

  it("envía el estado y la observación, y limpia el formulario al guardar", async () => {
    const patch = renderForm();

    await userEvent.click(screen.getByRole("radio", { name: "Priorizado" }));
    await userEvent.type(screen.getByLabelText(/Observación/), NOTE);
    expect(screen.getByText(`${NOTE.length}/1000`)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambio" }));

    expect(patch).toHaveBeenCalledWith(`/api/v1/admin/reports/${REPORT_ID}/status`, {
      status: "priorizado",
      note: NOTE,
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Estado actualizado.");
    expect(screen.getByLabelText(/Observación/)).toHaveValue("");
  });

  it("una observación en blanco se envía como null", async () => {
    const patch = renderForm();

    await userEvent.click(screen.getByRole("radio", { name: "Reparado" }));
    await userEvent.type(screen.getByLabelText(/Observación/), "   ");
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambio" }));

    expect(patch).toHaveBeenCalledWith(expect.any(String), { status: "reparado", note: null });
  });

  it("la observación no pasa de 1000 caracteres", () => {
    renderForm();

    expect(screen.getByLabelText(/Observación/)).toHaveAttribute("maxlength", "1000");
  });

  it("submit_disabled_while_sending: no permite el envío doble", async () => {
    let finish: (report: AdminReport) => void = () => {};
    const patch = renderForm(
      ["priorizado"],
      () =>
        new Promise<AdminReport>((resolve) => {
          finish = resolve;
        }),
    );

    await userEvent.click(screen.getByRole("radio", { name: "Priorizado" }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambio" }));

    const sending = await screen.findByRole("button", { name: "Guardando…" });
    expect(sending).toBeDisabled();
    await userEvent.click(sending);
    expect(patch).toHaveBeenCalledTimes(1);
    finish({ ...EVALUATED_REPORT, status: "priorizado" });
    expect(await screen.findByRole("status")).toHaveTextContent("Estado actualizado.");
  });

  it("conflict_409_shows_message_reloads_and_keeps_note: conserva lo escrito", async () => {
    const onConflict = vi.fn();
    const patch = vi.fn(async () => {
      throw new ApiError(
        409,
        "INVALID_STATUS_TRANSITION",
        "El reporte ya está reparado; no se puede pasar a priorizado.",
        { current_status: "reparado" },
      );
    });
    renderScreen(
      <StatusChangeForm
        reportId={REPORT_ID}
        allowedStatuses={["priorizado", "reparado"]}
        onConflict={onConflict}
      />,
      { api: { patch: patch as never } },
    );

    await userEvent.click(screen.getByRole("radio", { name: "Priorizado" }));
    await userEvent.type(screen.getByLabelText(/Observación/), NOTE);
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambio" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El reporte ya está reparado; no se puede pasar a priorizado.",
    );
    expect(onConflict).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText(/Observación/)).toHaveValue(NOTE);
  });

  it("si el estado elegido deja de estar permitido, se quita la selección y queda la nota", async () => {
    const { rerender } = renderRerenderable(["priorizado", "reparado"]);

    await userEvent.click(screen.getByRole("radio", { name: "Priorizado" }));
    await userEvent.type(screen.getByLabelText(/Observación/), NOTE);
    rerender(["reparado"]);

    expect(screen.queryByRole("radio", { name: "Priorizado" })).toBeNull();
    expect(screen.getByRole("radio", { name: "Reparado" })).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Guardar cambio" })).toBeDisabled();
    expect(screen.getByLabelText(/Observación/)).toHaveValue(NOTE);
  });
});

/** Permite cambiar `allowedStatuses` como lo haría la recarga del detalle. */
function renderRerenderable(initial: ReportStatus[]) {
  let setAllowed: (next: ReportStatus[]) => void = () => {};
  function Host() {
    const [allowed, set] = useState(initial);
    setAllowed = set;
    return <StatusChangeForm reportId={REPORT_ID} allowedStatuses={allowed} />;
  }
  renderScreen(<Host />);
  return { rerender: (next: ReportStatus[]) => act(() => setAllowed(next)) };
}
