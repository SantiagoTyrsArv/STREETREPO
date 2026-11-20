import { useRef } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { COPY } from "../content/copy";
import { useMagnetic } from "../interaction/useMagnetic";
import { Logo } from "./Logo";
import { ProximityText } from "../text/ProximityText";
import { HEADER_CTA_AXES } from "../text/proximity";
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
        <ProximityText text={COPY.header.download} by="char" axes={HEADER_CTA_AXES} />
      </a>
    </header>
  );
}
