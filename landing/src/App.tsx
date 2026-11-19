import { useReducedMotion } from "./a11y/useReducedMotion";
import { Formula } from "./chapters/Formula";
import { SEQUENCE_CHAPTERS, SequenceChapter } from "./chapters/SequenceChapter";
import { Logo } from "./components/Logo";
import { SiteHeader } from "./components/SiteHeader";
import { useSmoothScroll } from "./scroll/useSmoothScroll";
import type { ChapterId } from "./sequence/types";

function chapter(id: ChapterId) {
  const config = SEQUENCE_CHAPTERS.find((c) => c.id === id);
  if (!config) {
    throw new Error(`Capítulo desconocido: ${id}`);
  }
  return config;
}

export function App() {
  const still = useReducedMotion();
  useSmoothScroll(!still);

  return (
    <>
      <SiteHeader />
      <main id="contenido">
        <SequenceChapter
          chapter={chapter("apertura")}
          level="h1"
          introText
          before={<Logo variant="stacked" className="apertura__logo" />}
        />
        <SequenceChapter chapter={chapter("problema")} />
        <SequenceChapter chapter={chapter("priorizar")}>
          {(progress, isStill) => <Formula progress={progress} still={isStill} />}
        </SequenceChapter>
        <SequenceChapter chapter={chapter("reparado")} />
      </main>
      <div className="grain" aria-hidden="true" />
    </>
  );
}
