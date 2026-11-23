import { useRef, useState } from "react";
import { useIsomorphicLayoutEffect } from "../lib/useIsomorphicLayoutEffect";
import { letterFill, MASK_UNTIL, maskScale } from "./heroMaskScale";
import "./HeroMask.css";

const WORDS = ["STREET", "REPO"] as const;
const TEXT_PROPS = {
  x: "50%",
  y: "50%",
  textAnchor: "middle",
  dominantBaseline: "central",
} as const;

/**
 * Portada enmascarada: una capa de noche cubre la escena y solo la deja ver a través de
 * «STREET REPO». Las letras empiezan llenas de color; con la reproducción la capa crece desde el
 * asta de la «R» y el color se desvanece hasta dejar ver la escena.
 * Decorativa: el título accesible es el `h1` del capítulo.
 */
export function HeroMask({ progress }: { progress: number }) {
  const anchor = useRef<SVGTSpanElement>(null);
  const [origin, setOrigin] = useState("50% 50%");
  // Horizontal en el HTML prerenderizado; se ajusta antes de pintar, al hidratar.
  const [portrait, setPortrait] = useState(false);

  useIsomorphicLayoutEffect(() => {
    const onResize = () => setPortrait(window.innerHeight > window.innerWidth);
    onResize();
    window.addEventListener("resize", onResize, { passive: true });
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // El zoom sale del asta de la «R» de REPO (dentro de una letra): así la escena llena la pantalla.
  useIsomorphicLayoutEffect(() => {
    const span = anchor.current;
    if (!span || typeof span.getExtentOfChar !== "function") return;
    try {
      const box = span.getExtentOfChar(0);
      const svg = span.ownerSVGElement?.getBoundingClientRect();
      if (!svg || svg.width === 0) return;
      const x = ((box.x + box.width * 0.2) / svg.width) * 100;
      const y = ((box.y + box.height * 0.5) / svg.height) * 100;
      setOrigin(`${x.toFixed(2)}% ${y.toFixed(2)}%`);
    } catch {
      // Sin medidas (fuentes aún cargando): se queda el centro.
    }
  }, [portrait]);

  if (progress >= MASK_UNTIL) return null;
  // El mismo texto va en la máscara (agujero) y encima como contorno; el ancla de medida solo en uno.
  const letters = (measured: boolean) =>
    portrait ? (
      <>
        <tspan x="50%" dy="-0.5em">
          {WORDS[0]}
        </tspan>
        <tspan x="50%" dy="1em">
          <tspan ref={measured ? anchor : undefined}>R</tspan>EPO
        </tspan>
      </>
    ) : (
      <>
        {WORDS[0]} <tspan ref={measured ? anchor : undefined}>R</tspan>EPO
      </>
    );
  const fade = Math.min(1, Math.max(0, (progress - MASK_UNTIL * 0.6) / (MASK_UNTIL * 0.4)));

  return (
    <div
      className="hero-mask"
      aria-hidden="true"
      style={{
        transform: `scale(${maskScale(progress)})`,
        transformOrigin: origin,
        opacity: 1 - fade,
      }}
    >
      <svg className="hero-mask__svg" width="100%" height="100%">
        <defs>
          <mask id="hero-mask-letters">
            <rect width="100%" height="100%" fill="white" />
            <text className="hero-mask__text" {...TEXT_PROPS} fill="black">
              {letters(true)}
            </text>
          </mask>
        </defs>
        <rect
          className="hero-mask__night"
          width="100%"
          height="100%"
          mask="url(#hero-mask-letters)"
        />
        <text
          className="hero-mask__text hero-mask__fill"
          {...TEXT_PROPS}
          fillOpacity={letterFill(progress)}
        >
          {letters(false)}
        </text>
        <text className="hero-mask__text hero-mask__outline" {...TEXT_PROPS}>
          {letters(false)}
        </text>
      </svg>
    </div>
  );
}
