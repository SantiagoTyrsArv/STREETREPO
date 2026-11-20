import { describe, expect, it } from "vitest";
import {
  buildManifest,
  ffmpegArgs,
  parseArgs,
  parseDimensions,
  videoFilter,
} from "./build-sequences";

describe("parseArgs", () => {
  it("lee capítulo, videos y valores por defecto", () => {
    expect(parseArgs(["problema", "a.mp4", "b.mp4"])).toEqual({
      chapter: "problema",
      desktopVideo: "a.mp4",
      mobileVideo: "b.mp4",
      fps: 24,
      quality: 75,
    });
  });

  it("acepta --fps y --quality y deja el video móvil opcional", () => {
    const opts = parseArgs(["apertura", "a.mp4", "--fps", "12", "--quality", "60"]);
    expect(opts).toMatchObject({ mobileVideo: null, fps: 12, quality: 60 });
  });

  it("rechaza un capítulo desconocido, la falta de video y valores fuera de rango", () => {
    expect(() => parseArgs(["portada", "a.mp4"])).toThrow(/Capítulo inválido/);
    expect(() => parseArgs(["reparado"])).toThrow(/Falta el video/);
    expect(() => parseArgs(["reparado", "a.mp4", "--fps", "0"])).toThrow(/--fps/);
    expect(() => parseArgs(["reparado", "a.mp4", "--quality", "101"])).toThrow(/--quality/);
    expect(() => parseArgs(["reparado", "a.mp4", "--fps"])).toThrow(/Falta el valor/);
  });
});

describe("videoFilter", () => {
  it("recorta al centro en 9:16 solo cuando se pide", () => {
    expect(videoFilter(24, 1920, false)).toBe("fps=24,scale=1920:-2:flags=lanczos");
    expect(videoFilter(12, 1080, true)).toBe("fps=12,crop=ih*9/16:ih,scale=1080:-2:flags=lanczos");
  });
});

describe("ffmpegArgs", () => {
  it("codifica en WebP con la calidad pedida y numeración de cuatro cifras", () => {
    const args = ffmpegArgs("in.mp4", "out", "fps=24", 70);
    expect(args).toEqual(
      expect.arrayContaining(["-i", "in.mp4", "-c:v", "libwebp", "-quality", "70"]),
    );
    expect(args.at(-1)).toMatch(/out[\\/]frame_%04d\.webp$/);
  });
});

describe("parseDimensions", () => {
  it("lee el tamaño del cuadro de la salida de ffmpeg", () => {
    const stderr = "  Stream #0:0: Video: webp, yuv420p, 1920x1080, 25 fps";
    expect(parseDimensions(stderr)).toEqual({ width: 1920, height: 1080 });
    expect(() => parseDimensions("sin video")).toThrow();
  });
});

describe("buildManifest", () => {
  it("tiene la forma de SequenceManifest", () => {
    const dims = { desktop: { width: 1920, height: 1080 }, mobile: { width: 1080, height: 1920 } };
    expect(buildManifest("priorizar", 24, 193, dims)).toEqual({
      id: "priorizar",
      fps: 24,
      frameCount: 193,
      resolutions: dims,
    });
  });
});
