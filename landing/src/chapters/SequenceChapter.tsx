import { useRef, type ReactNode } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { RevealText } from "../components/RevealText";
import { SEQUENCE_COPY } from "../content/copy";
import { useChapterProgress } from "../scroll/useChapterProgress";
import { FrameSequence } from "../sequence/FrameSequence";
import type { ChapterId } from "../sequence/types";
import "./SequenceChapter.css";

type Accent = "amber" | "signal" | "repair" | "none";

export interface SequenceChapterConfig {
  id: ChapterId;
  /** Largo del recorrido fijado, en % del alto de la ventana. */
  pinLengthVh: number;
  accent: Accent;
}

/** Capítulos con escena generada, en el orden del guion (diseño, sección 6). */
export const SEQUENCE_CHAPTERS: readonly SequenceChapterConfig[] = [
  { id: "apertura", pinLengthVh: 250, accent: "none" },
  { id: "problema", pinLengthVh: 350, accent: "amber" },
  { id: "priorizar", pinLengthVh: 400, accent: "signal" },
  { id: "reparado", pinLengthVh: 300, accent: "repair" },
];

/** Fracción final del progreso en la que la escena se desvanece hacia la siguiente. */
const VANISH_FROM = 0.9;

interface SequenceChapterProps {
  chapter: SequenceChapterConfig;
  /** Contenido extra sobre la escena (p. ej. la fórmula), recibe el progreso. */
  children?: (progress: number, still: boolean) => ReactNode;
  /** Nivel del título: la apertura es el `h1` de la página. */
  level?: "h1" | "h2";
  /** Contenido sobre el antetítulo (la apertura muestra el logotipo). */
  before?: ReactNode;
  /** Texto visible desde la carga (portada), con una entrada propia en lugar del *scroll*. */
  introText?: boolean;
}

export function SequenceChapter({
  chapter,
  children,
  level = "h2",
  before,
  introText = false,
}: SequenceChapterProps) {
  const ref = useRef<HTMLElement>(null);
  const still = useReducedMotion();
  const progress = useChapterProgress(ref, { pinLengthVh: chapter.pinLengthVh, enabled: !still });
  const copy = SEQUENCE_COPY[chapter.id];

  const vanish = still ? 0 : Math.max(0, (progress - VANISH_FROM) / (1 - VANISH_FROM));
  const sceneStyle = still
    ? undefined
    : {
        opacity: 1 - vanish * 0.85,
        filter: `blur(${vanish * 14}px)`,
        transform: `scale(${1 + vanish * 0.04})`,
      };

  return (
    <section
      ref={ref}
      className={`chapter chapter--${chapter.accent}`}
      aria-labelledby={`${chapter.id}-titulo`}
    >
      <div className="chapter__scene" style={sceneStyle}>
        {still ? (
          <img className="chapter__still" src={`/media/${chapter.id}/key.webp`} alt={copy.alt} />
        ) : (
          <FrameSequence chapter={chapter.id} progress={progress} alt={copy.alt} />
        )}
        <div className="chapter__shade" aria-hidden="true" />
      </div>
      <div
        className={introText ? "chapter__content chapter__content--intro" : "chapter__content"}
        style={still ? undefined : { opacity: 1 - vanish }}
      >
        {before}
        <p className="chapter__kicker">{copy.kicker}</p>
        <RevealText
          as={level}
          id={`${chapter.id}-titulo`}
          className="chapter__title"
          text={copy.title}
          progress={progress}
          from={0.05}
          to={0.35}
          still={still || introText}
        />
        <RevealText
          className="chapter__lead"
          text={copy.lead}
          progress={progress}
          from={0.3}
          to={0.6}
          still={still || introText}
        />
        {children?.(progress, still)}
      </div>
    </section>
  );
}
