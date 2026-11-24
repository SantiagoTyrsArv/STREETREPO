import { useRef, useState, type ReactNode } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { RevealText } from "../components/RevealText";
import { SEQUENCE_COPY } from "../content/copy";
import { useDrift } from "../interaction/useDrift";
import { TitleLens } from "./TitleLens";
import { useChapterPlayback } from "../scroll/useChapterPlayback";
import { FrameSequence } from "../sequence/FrameSequence";
import type { ChapterId } from "../sequence/types";
import { ProximityText } from "../text/ProximityText";
import { KICKER_AXES, LEAD_AXES } from "../text/proximity";
import "./SequenceChapter.css";

type Accent = "amber" | "signal" | "repair" | "none";

export interface SequenceChapterConfig {
  id: ChapterId;
  /** Duración de la reproducción al entrar (diseño 4.1). */
  durationMs: number;
  accent: Accent;
  /** El título hace de lupa sobre la escena (Reparado). */
  lens?: boolean;
  /** El progreso sigue al *scroll* con la escena fija (la portada): nada avanza solo. */
  scrub?: boolean;
}

/**
 * Las escenas tienen 129 cuadros a 16 fps (unos 8 s): se reproducen a su velocidad real. Antes
 * duraban 3 a 4,5 s y pasaban demasiado rápido para apreciarlas (fila 133 de la bitácora).
 */
export const SCENE_DURATION_MS = 8000;

/** Capítulos con escena generada, en el orden del guion (diseño, sección 6). */
export const SEQUENCE_CHAPTERS: readonly SequenceChapterConfig[] = [
  { id: "apertura", durationMs: SCENE_DURATION_MS, accent: "none", scrub: true },
  { id: "problema", durationMs: SCENE_DURATION_MS, accent: "amber" },
  { id: "priorizar", durationMs: SCENE_DURATION_MS, accent: "signal" },
  { id: "reparado", durationMs: SCENE_DURATION_MS, accent: "repair", lens: true },
];

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
  /** Capa sobre la escena (la máscara de la portada y su indicador), recibe el progreso. */
  overlay?: (progress: number, still: boolean) => ReactNode;
  /** El texto aparece a partir de este progreso (la portada espera a atravesar las letras). */
  revealAfter?: number;
}

export function SequenceChapter({
  chapter,
  children,
  level = "h2",
  before,
  introText = false,
  overlay,
  revealAfter = 0,
}: SequenceChapterProps) {
  const ref = useRef<HTMLElement>(null);
  const still = useReducedMotion();
  const [framesReady, setFramesReady] = useState(false);
  const { progress, near } = useChapterPlayback(ref, {
    durationMs: chapter.durationMs,
    enabled: !still,
    ready: framesReady,
    scrub: chapter.scrub,
  });
  const copy = SEQUENCE_COPY[chapter.id];
  const driftRef = useRef<HTMLDivElement>(null);
  useDrift(driftRef, { enabled: !still });

  return (
    <section
      ref={ref}
      className={`chapter chapter--${chapter.accent}${chapter.scrub ? " chapter--scrub" : ""}`}
      id={chapter.id}
      data-accent={chapter.accent}
      aria-labelledby={`${chapter.id}-titulo`}
    >
      {/* En la portada la sección es más alta que la ventana y este contenedor queda fijo
          mientras el *scroll* avanza el zoom; en los demás capítulos ocupa la sección. */}
      <div className="chapter__pin">
        <div className="chapter__scene">
          {/* En reposo la escena «respira» (CSS) y se desplaza hacia el puntero o el dedo. */}
          <div className="chapter__breath">
            <div className="chapter__drift" ref={driftRef}>
              {still ? (
                <img
                  className="chapter__still"
                  src={`/media/${chapter.id}/key.webp`}
                  alt={copy.alt}
                />
              ) : (
                <FrameSequence
                  chapter={chapter.id}
                  progress={progress}
                  alt={copy.alt}
                  load={near}
                  onReady={() => setFramesReady(true)}
                />
              )}
            </div>
          </div>
          <div className="chapter__shade" aria-hidden="true" />
        </div>
        {overlay?.(progress, still)}
        <div
          className={introText ? "chapter__content chapter__content--intro" : "chapter__content"}
          style={
            still
              ? undefined
              : {
                  opacity:
                    revealAfter > 0 ? Math.min(1, Math.max(0, (progress - revealAfter) / 0.06)) : 1,
                }
          }
        >
          {before}
          <ProximityText
            as="p"
            className="chapter__kicker"
            text={copy.kicker}
            by="char"
            axes={KICKER_AXES}
          />
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
            proximity={LEAD_AXES}
            split="words"
            progress={progress}
            from={0.3}
            to={0.6}
            still={still || introText}
          />
          {children?.(progress, still)}
          {chapter.lens && !still ? <TitleLens section={ref} /> : null}
        </div>
      </div>
    </section>
  );
}
