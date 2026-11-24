import "@fontsource-variable/archivo/wdth.css";
import "@fontsource-variable/manrope/index.css";
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";
import "./styles/tokens.css";
import "./styles/global.css";
import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import { App } from "./App";
import { ScrollTrigger } from "./scroll/gsap";
import { resetScrollOnReload } from "./scroll/reloadToTop";

// Antes de hidratar: al recargar, la página vuelve a la portada. ScrollTrigger guarda la posición
// y la restaura al recalcular (y vuelve a poner `scrollRestoration` en `auto`): se borra esa memoria.
resetScrollOnReload(window, performance, () => ScrollTrigger.clearScrollMemory("manual"));

const root = document.getElementById("root");
if (!root) {
  throw new Error("Falta el elemento #root en index.html");
}
const app = (
  <StrictMode>
    <App />
  </StrictMode>
);
// La compilación trae la página prerenderizada (scripts/prerender.ts); `npm run dev`, no.
if (root.hasChildNodes()) {
  hydrateRoot(root, app);
} else {
  createRoot(root).render(app);
}
