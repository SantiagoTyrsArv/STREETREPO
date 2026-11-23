import { useRef, useState, type SVGProps } from "react";
import { useIsomorphicLayoutEffect } from "../lib/useIsomorphicLayoutEffect";
import { letterFill, MASK_UNTIL, maskScale } from "./heroMaskScale";
import "./HeroMask.css";

const WORDS = ["STREET", "REPO"] as const;
/** Misma consulta que el tamaño de las letras en HeroMask.css. */
const PORTRAIT_QUERY = "(orientation: portrait)";
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
  const landscapeAnchor = useRef<SVGTSpanElement>(null);
  const portraitAnchor = useRef<SVGTSpanElement>(null);
  const [origin, setOrigin] = useState("50% 50%");

  // El zoom sale del asta de la «R» de REPO (dentro de una letra): así la escena llena la pantalla.
  // Se mide la disposición visible y se vuelve a medir al girar o cambiar el tamaño.
  useIsomorphicLayoutEffect(() => {
    const measure = () => {
      const portrait = window.matchMedia(PORTRAIT_QUERY).matches;
      const span = (portrait ? portraitAnchor : landscapeAnchor).current;
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
    };
    measure();
    window.addEventListener("resize", measure, { passive: true });
    return () => window.removeEventListener("resize", measure);
  }, []);

  if (progress >= MASK_UNTIL) return null;
  // Las dos disposiciones van en el HTML y el CSS muestra una según la orientación: así la portada
  // prerenderizada ya sale bien en el celular, antes de que cargue el JavaScript. El mismo texto va
  // en la máscara (agujero), encima con color y como contorno; las anclas de medida, solo en uno.
  const letters = (className: string, props: SVGProps<SVGTextElement>, measured: boolean) => (
    <>
      <text className={`${className} hero-mask__text--landscape`} {...TEXT_PROPS} {...props}>
        {WORDS[0]} <tspan ref={measured ? landscapeAnchor : undefined}>R</tspan>EPO
      </text>
      <text className={`${className} hero-mask__text--portrait`} {...TEXT_PROPS} {...props}>
        <tspan x="50%" dy="-0.5em">
          {WORDS[0]}
        </tspan>
        <tspan x="50%" dy="1em">
          <tspan ref={measured ? portraitAnchor : undefined}>R</tspan>EPO
        </tspan>
      </text>
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
            {letters("hero-mask__text", { fill: "black" }, true)}
          </mask>
        </defs>
        <rect
          className="hero-mask__night"
          width="100%"
          height="100%"
          mask="url(#hero-mask-letters)"
        />
        {letters("hero-mask__text hero-mask__fill", { fillOpacity: letterFill(progress) }, false)}
        {letters("hero-mask__text hero-mask__outline", {}, false)}
      </svg>
    </div>
  );
}
