// Genera public/favicon.svg y public/apple-touch-icon.png desde el símbolo compacto.
// Uso: node scripts/build-icons.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { Resvg } from "@resvg/resvg-js";

const PAPER = "#F5F3EE";
const NIGHT = "#0A0E13";

const symbol = readFileSync("src/assets/brand/symbol-compact.svg", "utf8")
  .replace(' role="img" aria-label="Street Repo"', "")
  .replace("currentColor", PAPER);

writeFileSync("public/favicon.svg", symbol);

const padded = symbol.replace('viewBox="0 0 96 96"', 'viewBox="-14 -14 124 124"');
const png = new Resvg(padded, { fitTo: { mode: "width", value: 180 }, background: NIGHT })
  .render()
  .asPng();
writeFileSync("public/apple-touch-icon.png", png);
console.log("Íconos generados en public/.");
