import { useReducedMotion } from "./a11y/useReducedMotion";
import { AmbientBackground } from "./ambient/AmbientBackground";
import { Calculator } from "./calculator/Calculator";
import { Formula } from "./chapters/Formula";
import { HeroMask } from "./chapters/HeroMask";
import { MASK_UNTIL } from "./chapters/heroMaskScale";
import { Panel } from "./chapters/Panel";
import { Reportar } from "./chapters/Reportar";
import { SEQUENCE_CHAPTERS, SequenceChapter } from "./chapters/SequenceChapter";
import { DownloadSection } from "./components/DownloadSection";
import { Logo } from "./components/Logo";
import { ScrollCue } from "./components/ScrollCue";
import { SiteFooter } from "./components/SiteFooter";
import { SiteHeader } from "./components/SiteHeader";
import { SkipLink } from "./components/SkipLink";
import { RELEASE } from "./config/release";
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
      <SkipLink />
      <SiteHeader />
      <AmbientBackground />
      <main id="contenido">
        <SequenceChapter
          chapter={chapter("apertura")}
          level="h1"
          introText
          revealAfter={MASK_UNTIL * 0.9}
          overlay={(progress, isStill) =>
            isStill ? (
              <ScrollCue />
            ) : (
              <>
                <HeroMask progress={progress} />
                <ScrollCue />
              </>
            )
          }
          before={<Logo variant="stacked" className="apertura__logo" />}
        />
        <SequenceChapter chapter={chapter("problema")} />
        <Reportar />
        <SequenceChapter chapter={chapter("priorizar")}>
          {(progress, isStill) => <Formula progress={progress} still={isStill} />}
        </SequenceChapter>
        <Calculator />
        <Panel />
        <SequenceChapter chapter={chapter("reparado")} />
        <DownloadSection release={RELEASE} />
      </main>
      <SiteFooter />
      <div className="grain" aria-hidden="true" />
    </>
  );
}
