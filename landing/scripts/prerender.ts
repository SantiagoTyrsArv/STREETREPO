// Prerenderizado de la página (diseño 2026-11-23, escenas por pantalla): inyecta en
// `dist/index.html` el HTML que produce `src/entry-server.tsx`, para que los textos lleguen en la
// primera respuesta (LCP) y se lean sin JavaScript.
//
// Uso (lo llama `npm run build`, después de `vite build` y `vite build --ssr`):
//   node scripts/prerender.ts
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const CONTAINER = '<div id="root"></div>';

/** Sustituye el contenedor vacío de `index.html` por el mismo contenedor con la app dentro. */
export function injectApp(template: string, appHtml: string): string {
  if (!template.includes(CONTAINER)) {
    throw new Error(`Falta ${CONTAINER} en index.html`);
  }
  // Función de reemplazo: así un `$` del HTML no se interpreta como patrón.
  return template.replace(CONTAINER, () => `<div id="root">${appHtml}</div>`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = join(dirname(fileURLToPath(import.meta.url)), "..");
  const indexPath = join(root, "dist", "index.html");
  const entry = pathToFileURL(join(root, "dist-ssr", "entry-server.js")).href;
  const { render } = (await import(entry)) as { render: () => string };
  writeFileSync(indexPath, injectApp(readFileSync(indexPath, "utf8"), render()));
  console.log("Página prerenderizada en dist/index.html.");
}
