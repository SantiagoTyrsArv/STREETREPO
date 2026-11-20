import { useRef } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { COPY } from "../content/copy";
import { useMagnetic } from "../interaction/useMagnetic";
import { Logo } from "./Logo";
import "./SiteHeader.css";

export function SiteHeader() {
  const ctaRef = useRef<HTMLAnchorElement>(null);
  useMagnetic(ctaRef, !useReducedMotion());
  return (
    <header className="site-header">
      <a className="site-header__brand" href="#contenido" aria-label="Street Repo, inicio">
        <Logo variant="horizontal" />
      </a>
      <a ref={ctaRef} className="site-header__cta" href="#descarga">
        {COPY.header.download}
      </a>
    </header>
  );
}
