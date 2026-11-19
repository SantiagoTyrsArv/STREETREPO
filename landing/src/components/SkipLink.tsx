import { COPY } from "../content/copy";
import "./SkipLink.css";

/** Primer elemento enfocable: lleva el teclado directo a la descarga, sin recorrer las escenas. */
export function SkipLink() {
  return (
    <a className="skip-link" href="#descarga">
      {COPY.skipLink}
    </a>
  );
}
