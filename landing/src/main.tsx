import "@fontsource-variable/archivo/wdth.css";
import "@fontsource-variable/manrope/index.css";
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";
import "./styles/tokens.css";
import "./styles/global.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Falta el elemento #root en index.html");
}
createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
