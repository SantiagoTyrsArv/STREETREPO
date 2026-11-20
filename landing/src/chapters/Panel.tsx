import { useRef } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { RevealText } from "../components/RevealText";
import { COPY } from "../content/copy";
import { useChapterProgress } from "../scroll/useChapterProgress";
import "./Panel.css";

/** Largo del recorrido fijado, en % del alto de la ventana. */
const PIN_LENGTH_VH = 250;
/** Tramo del progreso en el que la captura pasa de inclinada a frontal. */
const SETTLE_UNTIL = 0.6;

const OSM_ATTRIBUTION = "Mapa: © colaboradores de OpenStreetMap";

export function Panel() {
  const ref = useRef<HTMLElement>(null);
  const still = useReducedMotion();
  const progress = useChapterProgress(ref, { pinLengthVh: PIN_LENGTH_VH, enabled: !still });
  const copy = COPY.panel;

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
      className="panel"
      aria-labelledby="panel-titulo"
      data-accent="signal"
      data-ambient="visible"
    >
      <div className="panel__glow" style={glowStyle} aria-hidden="true" />
      <div className="panel__content">
        <p className="panel__kicker">{copy.kicker}</p>
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
          progress={progress}
          from={0.2}
          to={0.45}
          still={still}
        />
      </div>
      <div className="panel__stage">
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
    </section>
  );
}
