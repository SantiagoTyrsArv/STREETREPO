import { useRef } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { RevealText } from "../components/RevealText";
import { COPY } from "../content/copy";
import { useChapterProgress } from "../scroll/useChapterProgress";
import { PhoneStage } from "../three/PhoneStage";
import "./Reportar.css";

/** Largo del recorrido fijado: cuatro capturas necesitan más recorrido que una escena. */
const PIN_LENGTH_VH = 400;

export function Reportar() {
  const ref = useRef<HTMLElement>(null);
  const still = useReducedMotion();
  const progress = useChapterProgress(ref, { pinLengthVh: PIN_LENGTH_VH, enabled: !still });
  const copy = COPY.reportar;

  return (
    <section ref={ref} className="reportar" aria-labelledby="reportar-titulo">
      <div className="reportar__content">
        <p className="reportar__kicker">{copy.kicker}</p>
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
