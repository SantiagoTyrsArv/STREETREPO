import { useEffect, useId, useRef, useState } from "react";
import { COPY } from "../content/copy";
import { Calculator } from "./Calculator";
import "./CalculatorBubble.css";

/** Sección tras la cual aparece la burbuja (la portada) y la que la oculta (la descarga). */
const AFTER_ID = "apertura";
const HIDE_ID = "descarga";

/**
 * La burbuja se ve después de la portada y se esconde en la descarga, para no tapar su botón.
 * Sin `IntersectionObserver` (navegadores viejos) queda siempre visible.
 */
function useBubbleVisible(): boolean {
  const [pastHero, setPastHero] = useState(false);
  const [atDownload, setAtDownload] = useState(false);
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      setPastHero(true);
      return undefined;
    }
    const hero = document.getElementById(AFTER_ID);
    const download = document.getElementById(HIDE_ID);
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === hero) {
          // Pasada la portada = ya no se ve y quedó arriba de la ventana.
          setPastHero(!entry.isIntersecting && entry.boundingClientRect.top < 0);
        } else if (entry.target === download) {
          setAtDownload(entry.isIntersecting);
        }
      }
    });
    if (hero) observer.observe(hero);
    else setPastHero(true);
    if (download) observer.observe(download);
    return () => observer.disconnect();
  }, []);
  return pastHero && !atDownload;
}

/**
 * «Pruébalo» como botón burbuja flotante (fila 133 de la bitácora): abre la calculadora en un
 * panel no modal sobre la página. Escape o el botón de cerrar lo cierran y el foco vuelve a la
 * burbuja.
 */
export function CalculatorBubble() {
  const copy = COPY.calculadora;
  const id = useId();
  const panelId = `${id}-panel`;
  const titleId = `${id}-titulo`;
  const visible = useBubbleVisible();
  const [open, setOpen] = useState(false);
  const bubbleRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const close = (returnFocus = true) => {
    setOpen(false);
    if (returnFocus) bubbleRef.current?.focus();
  };

  useEffect(() => {
    if (!visible) setOpen(false);
  }, [visible]);

  useEffect(() => {
    if (!open) return undefined;
    panelRef.current?.querySelector<HTMLElement>("input, select, button")?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        bubbleRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="calc-bubble" data-visible={visible ? "true" : "false"}>
      {open ? (
        <div
          ref={panelRef}
          id={panelId}
          className="calc-bubble__panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby={titleId}
          data-lenis-prevent=""
        >
          <button
            type="button"
            className="calc-bubble__close"
            aria-label={copy.close}
            onClick={() => close()}
          >
            <span aria-hidden="true">×</span>
          </button>
          <Calculator titleId={titleId} />
        </div>
      ) : null}
      <button
        ref={bubbleRef}
        type="button"
        className="calc-bubble__button"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        tabIndex={visible ? 0 : -1}
        aria-hidden={visible ? undefined : true}
        onClick={() => (open ? close() : setOpen(true))}
      >
        <span className="calc-bubble__glyph" aria-hidden="true">
          U
        </span>
        <span className="calc-bubble__label">{copy.open}</span>
      </button>
    </div>
  );
}
