import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FrameSequence } from "./FrameSequence";
import { createFrameLoader, frameUrl } from "./loader";
import type * as LoaderModule from "./loader";
import type { SequenceManifest } from "./types";

// El cargador real usa <img> que jsdom nunca termina de cargar: se sustituye por uno que avisa
// a mano. frameUrl sigue siendo el real.
vi.mock("./loader", async (importOriginal) => {
  const actual = await importOriginal<typeof LoaderModule>();
  return {
    ...actual,
    createFrameLoader: vi.fn(
      (_base: string, _manifest: unknown, _res: unknown, onFrame?: (i: number) => void) => {
        const loaded = new Set<number>();
        return {
          start: () => undefined,
          cancel: () => undefined,
          get: () => undefined,
          loaded,
          finish: (index: number) => {
            loaded.add(index);
            onFrame?.(index);
          },
        };
      },
    ),
  };
});

type FakeLoader = ReturnType<typeof createFrameLoader> & { finish: (index: number) => void };
const loaderMock = vi.mocked(createFrameLoader);

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
      <FrameSequence
        chapter="problema"
        progress={0}
        alt="Una calle de Pasto bajo la lluvia"
        load
      />,
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

    const { container } = render(
      <FrameSequence chapter="problema" progress={0} alt="Calle" load />,
    );

    await waitFor(() => {
      expect(container.querySelector("img")).toHaveAttribute("src", "/media/problema/key.webp");
    });
  });

  it("no descarga cuadros mientras load es false", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(MANIFEST)));
    vi.stubGlobal("fetch", fetchMock);
    loaderMock.mockClear();

    const { rerender } = render(
      <FrameSequence chapter="problema" progress={0} alt="Calle" load={false} />,
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    await act(async () => undefined);
    expect(loaderMock).not.toHaveBeenCalled();

    rerender(<FrameSequence chapter="problema" progress={0} alt="Calle" load />);
    await waitFor(() => expect(loaderMock).toHaveBeenCalledTimes(1));
  });

  it("avisa una vez cuando todos los cuadros están cargados", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(MANIFEST))));
    loaderMock.mockClear();
    const onReady = vi.fn();

    render(<FrameSequence chapter="problema" progress={0} alt="Calle" load onReady={onReady} />);
    await waitFor(() => expect(loaderMock).toHaveBeenCalled());
    const loader = loaderMock.mock.results[0]!.value as FakeLoader;

    act(() => {
      loader.finish(0);
      loader.finish(1);
    });
    expect(onReady).not.toHaveBeenCalled();
    act(() => loader.finish(2));
    expect(onReady).toHaveBeenCalledTimes(1);
    act(() => loader.finish(2));
    expect(onReady).toHaveBeenCalledTimes(1);
  });
});
