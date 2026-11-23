// Presupuesto de peso de la página (diseño 2026-11-19, sección 7): ≤ 6 MB antes del primer
// capítulo interactivo, ≤ 45 MB en total en escritorio y ≤ 25 MB en móvil.
//
// Uso (después de `npm run build`, porque las fuentes se miden en dist/assets):
//   node scripts/check-media-budget.ts
// Sale con 1 si algo se pasa del presupuesto.
import { existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

export interface Sizes {
  initialBytes: number;
  desktopBytes: number;
  mobileBytes: number;
}

/** MB decimales, como los del diseño. */
export const BUDGET: Sizes = { initialBytes: 6e6, desktopBytes: 45e6, mobileBytes: 25e6 };

const LABELS: Record<keyof Sizes, string> = {
  initialBytes: "carga inicial",
  desktopBytes: "total en escritorio",
  mobileBytes: "total en móvil",
};

const FONT = /\.(woff2?|ttf|otf)$/;

function mb(bytes: number): string {
  return `${Math.round(bytes / 1e5) / 10} MB`.replace(".", ",");
}

/** Incumplimientos del presupuesto; vacío si cumple. */
export function checkBudget(sizes: Sizes): string[] {
  return (Object.keys(BUDGET) as (keyof Sizes)[])
    .filter((key) => sizes[key] > BUDGET[key])
    .map((key) => `La ${LABELS[key]} pesa ${mb(sizes[key])}; el límite es ${mb(BUDGET[key])}.`);
}

function files(dir: string): { path: string; bytes: number }[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => {
      const path = join(entry.parentPath, entry.name);
      return { path: relative(dir, path).split(sep).join("/"), bytes: statSync(path).size };
    });
}

const sum = (list: { bytes: number }[]) => list.reduce((total, f) => total + f.bytes, 0);

/**
 * Mide `landing/` (raíz `root`). Los cuadros viven en `media/<capítulo>/{desktop,mobile}/`; lo demás
 * de `media/` lo cargan las dos resoluciones. La carga inicial es la portada (`apertura/`) de la
 * resolución más pesada, más las fuentes compiladas y el ícono: una cota superior, porque el
 * navegador solo baja los subconjuntos de fuente que usa.
 */
export function measure(root: string): Sizes {
  const media = files(join(root, "public", "media"));
  const isRes = (res: string) => (f: { path: string }) => f.path.split("/")[1] === res;
  const shared = media.filter((f) => !isRes("desktop")(f) && !isRes("mobile")(f));
  const desktop = media.filter(isRes("desktop"));
  const mobile = media.filter(isRes("mobile"));

  const inApertura = (f: { path: string }) => f.path.startsWith("apertura/");
  const fonts = files(join(root, "dist", "assets")).filter((f) => FONT.test(f.path));
  const favicon = files(join(root, "public")).filter((f) => f.path.startsWith("favicon"));
  const initialCommon = sum(shared.filter(inApertura)) + sum(fonts) + sum(favicon);

  return {
    desktopBytes: sum(shared) + sum(desktop),
    mobileBytes: sum(shared) + sum(mobile),
    initialBytes:
      initialCommon + Math.max(sum(desktop.filter(inApertura)), sum(mobile.filter(inApertura))),
  };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = join(dirname(fileURLToPath(import.meta.url)), "..");
  const sizes = measure(root);
  console.log(
    `Carga inicial ${mb(sizes.initialBytes)} · escritorio ${mb(sizes.desktopBytes)} · móvil ${mb(sizes.mobileBytes)}`,
  );
  const problems = checkBudget(sizes);
  for (const problem of problems) console.error(problem);
  process.exitCode = problems.length > 0 ? 1 : 0;
}
