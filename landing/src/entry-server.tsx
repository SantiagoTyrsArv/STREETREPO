import { StrictMode } from "react";
import { renderToString } from "react-dom/server";
import { App } from "./App";

/**
 * HTML de la página para el prerenderizado (`scripts/prerender.ts`): el mismo árbol que monta
 * `main.tsx`, de modo que el cliente lo hidrata sin diferencias.
 */
export function render(): string {
  return renderToString(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
