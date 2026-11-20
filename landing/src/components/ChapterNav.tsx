import { useEffect, useState } from "react";
import { COPY } from "../content/copy";
import { pickActive } from "./chapters";
import "./ChapterNav.css";

interface ChapterNavProps {
  chapters: readonly { id: string; label: string }[];
}

/**
 * Barra de progreso por capítulos: puntos a la derecha (escritorio) que llevan a cada capítulo y
 * marcan el que se está viendo; en el celular, una línea fina arriba con el avance total.
 */
export function ChapterNav({ chapters }: ChapterNavProps) {
  const [active, setActive] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const entries = chapters.flatMap(({ id }) => {
        const el = document.getElementById(id);
        if (!el) return [];
        const r = el.getBoundingClientRect();
        return [{ id, top: r.top, height: r.height }];
      });
      setActive(pickActive(entries, window.innerHeight));
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule, { passive: true });
    return () => {
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [chapters]);

  return (
    <>
      <div className="chapter-line" aria-hidden="true">
        <span style={{ transform: `scaleX(${progress})` }} />
      </div>
      <nav className="chapter-nav" aria-label={COPY.chapterNav.label}>
        <ol>
          {chapters.map(({ id, label }) => (
            <li key={id}>
              <a
                href={`#${id}`}
                className="chapter-nav__dot"
                aria-current={active === id ? "true" : undefined}
              >
                <span className="chapter-nav__label">{label}</span>
              </a>
            </li>
          ))}
        </ol>
      </nav>
    </>
  );
}
