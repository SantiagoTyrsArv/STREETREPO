import { useEffect, useState } from "react";
import { COPY } from "../content/copy";
import "./ScrollCue.css";

/** Desde cuántos píxeles de *scroll* se da por entendido y se retira. */
const DISMISS_AFTER = 40;

/** Indicador «Desliza» de la portada: se va para siempre al empezar el *scroll*. */
export function ScrollCue() {
  const [gone, setGone] = useState(false);
  useEffect(() => {
    if (gone) return;
    const onScroll = () => {
      if (window.scrollY > DISMISS_AFTER) setGone(true);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [gone]);
  if (gone) return null;
  return (
    <div className="scroll-cue">
      <span className="scroll-cue__label">{COPY.scrollCue}</span>
      <span className="scroll-cue__track" aria-hidden="true">
        <span className="scroll-cue__dot" />
      </span>
    </div>
  );
}
