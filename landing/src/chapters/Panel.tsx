import { useRef } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { RevealText } from "../components/RevealText";
import { COPY } from "../content/copy";
import { useTilt } from "../interaction/useTilt";
import { useChapterPlayback } from "../scroll/useChapterPlayback";
import { ProximityText } from "../text/ProximityText";
import { KICKER_AXES, LEAD_AXES } from "../text/proximity";
import "./Panel.css";

/** Duración de la reproducción al entrar (diseño 4.1). */
const DURATION_MS = 2500;
/** Tramo del progreso en el que la captura pasa de inclinada a frontal. */
const SETTLE_UNTIL = 0.6;

const OSM_ATTRIBUTION = "Mapa: © colaboradores de OpenStreetMap";

export function Panel() {
  const ref = useRef<HTMLElement>(null);
  const still = useReducedMotion();
  // Sin secuencia de cuadros: no hay nada que esperar.
  const { progress } = useChapterPlayback(ref, {
    durationMs: DURATION_MS,
    enabled: !still,
    ready: true,
  });
  const copy = COPY.panel;
  const tiltRef = useRef<HTMLDivElement>(null);
  useTilt(tiltRef, { enabled: !still });

  const settle = still ? 1 : Math.min(1, progress / SETTLE_UNTIL);
  const eased = 1 - (1 - settle) ** 3;
  const screenStyle = still
    ? undefined
    : {
        transform: `rotateX(${(1 - eased) * 32}deg) rotateZ(${(1 - eased) * -6}deg) translateY(${(1 - eased) * 18}%) scale(${0.86 + eased * 0.14})`,
        opacity: 0.35 + eased * 0.65,
      };
  // Paralaje: el reflejo se desplaza más lento que la captura.
  const glowStyle = still ? undefined : { transform: `translateY(${(1 - progress) * 30}%)` };

  return (
    <section
      ref={ref}
      id="panel"
      className="panel"
      aria-labelledby="panel-titulo"
      data-accent="signal"
      data-ambient="visible"
    >
      <div className="panel__glow" style={glowStyle} aria-hidden="true" />
      <div className="panel__content">
        <ProximityText
          as="p"
          className="panel__kicker"
          text={copy.kicker}
          by="char"
          axes={KICKER_AXES}
        />
        <RevealText
          as="h2"
          id="panel-titulo"
          className="panel__title"
          text={copy.title}
          progress={progress}
          from={0.02}
          to={0.25}
          still={still}
        />
        <RevealText
          className="panel__lead"
          text={copy.lead}
          proximity={LEAD_AXES}
          split="words"
          progress={progress}
          from={0.2}
          to={0.45}
          still={still}
        />
      </div>
      <div className="panel__stage">
        <div className="panel__tilt" ref={tiltRef}>
          <figure className="panel__screen" style={screenStyle}>
            <img
              src="/media/panel/priorizacion.webp"
              alt={copy.alt}
              width={1600}
              height={1111}
              loading="lazy"
              decoding="async"
            />
            <figcaption className="panel__attribution">{OSM_ATTRIBUTION}</figcaption>
          </figure>
        </div>
      </div>
    </section>
  );
}
