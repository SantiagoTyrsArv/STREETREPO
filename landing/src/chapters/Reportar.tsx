import { useRef } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { RevealText } from "../components/RevealText";
import { COPY } from "../content/copy";
import { useChapterPlayback } from "../scroll/useChapterPlayback";
import { PhoneStage } from "../three/PhoneStage";
import { ProximityText } from "../text/ProximityText";
import { KICKER_AXES, LEAD_AXES } from "../text/proximity";
import "./Reportar.css";

/** Duración de la reproducción al entrar (diseño 4.1). */
const DURATION_MS = 6000;

export function Reportar() {
  const ref = useRef<HTMLElement>(null);
  const still = useReducedMotion();
  // Sin secuencia de cuadros: no hay nada que esperar.
  const { progress } = useChapterPlayback(ref, {
    durationMs: DURATION_MS,
    enabled: !still,
    ready: true,
  });
  const copy = COPY.reportar;

  return (
    <section
      ref={ref}
      id="reportar"
      className="reportar"
      aria-labelledby="reportar-titulo"
      data-accent="amber"
      data-ambient="visible"
    >
      <div className="reportar__content">
        <ProximityText
          as="p"
          className="reportar__kicker"
          text={copy.kicker}
          by="char"
          axes={KICKER_AXES}
        />
        <RevealText
          as="h2"
          id="reportar-titulo"
          className="reportar__title"
          text={copy.title}
          progress={progress}
          from={0.02}
          to={0.2}
          still={still}
        />
        <RevealText
          className="reportar__lead"
          text={copy.lead}
          proximity={LEAD_AXES}
          split="words"
          progress={progress}
          from={0.15}
          to={0.35}
          still={still}
        />
      </div>
      <PhoneStage progress={progress} screens={copy.screens} />
    </section>
  );
}
