import { COPY } from "../content/copy";
import { Logo } from "./Logo";
import "./SiteFooter.css";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <Logo variant="horizontal" />
      <p className="site-footer__project">{COPY.footer.project}</p>
      <p className="site-footer__notice">
        {COPY.footer.aiNotice} · {new Date().getFullYear()}
      </p>
    </footer>
  );
}
