import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { fakeApi, fakeSession, WithSession } from "../test/session";
import { AuthImage } from "./AuthImage";

const createObjectURL = vi.fn(() => "blob:foto-1");
const revokeObjectURL = vi.fn();

beforeEach(() => {
  // jsdom no implementa las URL de objeto.
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL, revokeObjectURL }));
});

afterEach(() => {
  createObjectURL.mockClear();
  revokeObjectURL.mockClear();
});

function renderImage(getBlob: (path: string) => Promise<Blob>) {
  return render(
    <WithSession session={fakeSession({ api: fakeApi({ getBlob }) })}>
      <AuthImage src="/api/v1/reports/9/photo/thumbnail" alt="Foto del daño" />
    </WithSession>,
  );
}

describe("imagen autenticada", () => {
  it("pide la imagen con la sesión y la muestra", async () => {
    const getBlob = vi.fn(async () => new Blob(["x"], { type: "image/jpeg" }));

    renderImage(getBlob);

    expect(await screen.findByRole("img", { name: "Foto del daño" })).toHaveAttribute(
      "src",
      "blob:foto-1",
    );
    expect(getBlob).toHaveBeenCalledWith("/api/v1/reports/9/photo/thumbnail");
  });

  it("revokes_object_url_on_unmount: libera la URL al desmontar", async () => {
    const view = renderImage(async () => new Blob(["x"], { type: "image/jpeg" }));
    await screen.findByRole("img", { name: "Foto del daño" });
    expect(revokeObjectURL).not.toHaveBeenCalled();

    view.unmount();

    expect(revokeObjectURL).toHaveBeenCalledWith("blob:foto-1");
  });

  it("si la imagen no carga, lo dice con texto", async () => {
    renderImage(async () => {
      throw new ApiError(404, "REPORT_PHOTO_NOT_FOUND", "Sin foto");
    });

    expect(await screen.findByText("No se pudo cargar la imagen.")).toBeInTheDocument();
    expect(screen.queryByRole("img")).toBeNull();
  });
});
