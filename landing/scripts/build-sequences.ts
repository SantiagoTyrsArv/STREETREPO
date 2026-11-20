// Convierte el video aprobado de una escena en la secuencia de cuadros WebP que dibuja
// <FrameSequence>: public/media/<capítulo>/{desktop,mobile}/frame_0001.webp…, key.webp y manifest.json.
//
// Uso (Node ≥ 22.18, que ejecuta TypeScript sin compilar):
//   node scripts/build-sequences.ts <capítulo> <video 16:9> [video 9:16] [--fps 24] [--quality 75]
// Sin video 9:16, la versión móvil es un recorte centrado del 16:9.
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import ffmpegPath from "ffmpeg-static";

export const CHAPTERS = ["apertura", "problema", "priorizar", "reparado"] as const;
export type Chapter = (typeof CHAPTERS)[number];
type Resolution = "desktop" | "mobile";

// Ancho nativo de los videos (720p de Seedance 2.5): escalar a 1920/1080 solo sumaba peso, no
// detalle; el lienzo ya escala al dibujar con devicePixelRatio.
export const DESKTOP_WIDTH = 1280;
export const MOBILE_WIDTH = 720;

export interface BuildOptions {
  chapter: Chapter;
  desktopVideo: string;
  mobileVideo: string | null;
  fps: number;
  quality: number;
}

export function parseArgs(argv: readonly string[]): BuildOptions {
  const positional: string[] = [];
  const flags: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i] as string;
    if (arg.startsWith("--")) {
      const value = argv[i + 1];
      if (value === undefined) throw new Error(`Falta el valor de ${arg}.`);
      flags[arg.slice(2)] = value;
      i++;
    } else {
      positional.push(arg);
    }
  }
  const [chapter, desktopVideo, mobileVideo] = positional;
  if (!chapter || !(CHAPTERS as readonly string[]).includes(chapter)) {
    throw new Error(`Capítulo inválido: «${chapter ?? ""}». Usa uno de: ${CHAPTERS.join(", ")}.`);
  }
  if (!desktopVideo) throw new Error("Falta el video 16:9.");
  const fps = Number(flags.fps ?? 24);
  const quality = Number(flags.quality ?? 75);
  if (!Number.isInteger(fps) || fps < 1 || fps > 60)
    throw new Error("--fps debe ser un entero 1–60.");
  if (!Number.isInteger(quality) || quality < 1 || quality > 100) {
    throw new Error("--quality debe ser un entero 1–100.");
  }
  return {
    chapter: chapter as Chapter,
    desktopVideo,
    mobileVideo: mobileVideo ?? null,
    fps,
    quality,
  };
}

/** Filtro de ffmpeg para una resolución; `cropToPortrait` recorta al centro en 9:16. */
export function videoFilter(fps: number, width: number, cropToPortrait: boolean): string {
  const crop = cropToPortrait ? "crop=ih*9/16:ih," : "";
  return `fps=${fps},${crop}scale=${width}:-2:flags=lanczos`;
}

export function ffmpegArgs(
  input: string,
  outDir: string,
  filter: string,
  quality: number,
): string[] {
  return [
    "-v",
    "error",
    "-y",
    "-i",
    input,
    "-vf",
    filter,
    "-c:v",
    "libwebp",
    "-quality",
    String(quality),
    "-compression_level",
    "6",
    join(outDir, "frame_%04d.webp"),
  ];
}

export function buildManifest(
  id: Chapter,
  fps: number,
  frameCount: number,
  resolutions: Record<Resolution, { width: number; height: number }>,
) {
  return { id, fps, frameCount, resolutions };
}

/** Lee «WxH» de la salida de `ffmpeg -i` (el paquete no trae ffprobe). */
export function parseDimensions(ffmpegStderr: string): { width: number; height: number } {
  const match = /Video:.*?(\d{2,5})x(\d{2,5})/.exec(ffmpegStderr);
  if (!match) throw new Error("No se pudieron leer las dimensiones del cuadro.");
  return { width: Number(match[1]), height: Number(match[2]) };
}

function run(ffmpeg: string, args: string[]): string {
  const result = spawnSync(ffmpeg, args, { encoding: "utf8" });
  if (result.error) throw result.error;
  return result.stderr;
}

function encode(ffmpeg: string, input: string, outDir: string, filter: string, quality: number) {
  rmSync(outDir, { recursive: true, force: true });
  mkdirSync(outDir, { recursive: true });
  const stderr = run(ffmpeg, ffmpegArgs(input, outDir, filter, quality));
  const frames = readdirSync(outDir).filter((f) => f.endsWith(".webp")).length;
  if (frames === 0) throw new Error(`ffmpeg no generó cuadros para ${input}:\n${stderr}`);
  const dims = parseDimensions(
    run(ffmpeg, ["-hide_banner", "-i", join(outDir, "frame_0001.webp")]),
  );
  return { frames, dims };
}

function main(): void {
  if (!ffmpegPath || !existsSync(ffmpegPath)) {
    throw new Error("No se encontró ffmpeg: ejecuta «npm install» en landing/ (ffmpeg-static).");
  }
  const opts = parseArgs(process.argv.slice(2));
  for (const video of [opts.desktopVideo, opts.mobileVideo]) {
    if (video && !existsSync(video)) throw new Error(`No existe el video: ${video}`);
  }
  const base = join("public", "media", opts.chapter);
  const desktop = encode(
    ffmpegPath,
    opts.desktopVideo,
    join(base, "desktop"),
    videoFilter(opts.fps, DESKTOP_WIDTH, false),
    opts.quality,
  );
  const mobile = encode(
    ffmpegPath,
    opts.mobileVideo ?? opts.desktopVideo,
    join(base, "mobile"),
    videoFilter(opts.fps, MOBILE_WIDTH, opts.mobileVideo === null),
    opts.quality,
  );
  // Las dos versiones vienen de videos de la misma duración; si difieren en un cuadro,
  // el manifiesto anuncia solo los que existen en ambas.
  const frameCount = Math.min(desktop.frames, mobile.frames);
  copyFileSync(join(base, "desktop", "frame_0001.webp"), join(base, "key.webp"));
  const manifest = buildManifest(opts.chapter, opts.fps, frameCount, {
    desktop: desktop.dims,
    mobile: mobile.dims,
  });
  writeFileSync(join(base, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(
    `${opts.chapter}: ${frameCount} cuadros a ${opts.fps} fps · escritorio ${desktop.dims.width}×${desktop.dims.height} · móvil ${mobile.dims.width}×${mobile.dims.height}`,
  );
}

if (import.meta.main) {
  try {
    main();
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  }
}
