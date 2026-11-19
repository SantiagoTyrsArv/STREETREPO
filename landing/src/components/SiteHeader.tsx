import { COPY } from "../content/copy";
import { Logo } from "./Logo";
import "./SiteHeader.css";

export function SiteHeader() {
  return (
    <header className="site-header">
      <a className="site-header__brand" href="#contenido" aria-label="Street Repo, inicio">
        <Logo variant="horizontal" />
      </a>
      <a className="site-header__cta" href="#descarga">
        {COPY.header.download}
      </a>
    </header>
  );
}
