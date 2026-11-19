import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FrameSequence } from "./FrameSequence";
import { frameUrl } from "./loader";
import type { SequenceManifest } from "./types";

const MANIFEST: SequenceManifest = {
  id: "problema",
  fps: 24,
  frameCount: 3,
  resolutions: { desktop: { width: 1920, height: 1080 }, mobile: { width: 1080, height: 1920 } },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("frameUrl", () => {
  it("numera los cuadros desde 0001 dentro de la carpeta de la resolución", () => {
    expect(frameUrl("/media/problema", "mobile", 0)).toBe("/media/problema/mobile/frame_0001.webp");
    expect(frameUrl("/media/problema", "desktop", 119)).toBe(
      "/media/problema/desktop/frame_0120.webp",
    );
  });
});

describe("FrameSequence", () => {
  it("se anuncia como imagen con su texto alternativo y pide el manifiesto del capítulo", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(MANIFEST)));
    vi.stubGlobal("fetch", fetchMock);

    render(
      <FrameSequence chapter="problema" progress={0} alt="Una calle de Pasto bajo la lluvia" />,
    );

    expect(
      screen.getByRole("img", { name: "Una calle de Pasto bajo la lluvia" }),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/media/problema/manifest.json");
    });
  });

  it("si el manifiesto no carga, sigue mostrando el cuadro clave como respaldo", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("sin red")));

    const { container } = render(<FrameSequence chapter="problema" progress={0} alt="Calle" />);

    await waitFor(() => {
      expect(container.querySelector("img")).toHaveAttribute("src", "/media/problema/key.webp");
    });
  });
});
