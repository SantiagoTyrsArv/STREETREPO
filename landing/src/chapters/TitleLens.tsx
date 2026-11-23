import gsap from "gsap";
import { useEffect, useRef, type RefObject } from "react";
import { useClientCheck } from "../lib/useClientCheck";
import { trackVisibility } from "../interaction/visibility";
import "./TitleLens.css";

/** Cuánto se realza la escena dentro de las letras. */
const LENS_FILTER = "brightness(1.8) contrast(1.1) saturate(1.15)";
/** Velo de papel dentro de las letras (0–1): asegura que se lean sobre zonas oscuras. */
const LENS_FLOOR = 0.3;

function canvas2dAvailable(): boolean {
  try {
    return Boolean(document.createElement("canvas").getContext("2d"));
  } catch {
    return false;
  }
}

/**
 * Lupa: el título del capítulo deja ver la escena más clara y nítida dentro de sus letras. Un lienzo
 * del tamaño del título copia en cada cuadro el trozo de la escena que tiene detrás, lo realza y lo
 * recorta con las palabras en su posición real. El `h2` sigue en la página (accesible); solo su
 * relleno se vuelve transparente mientras la lupa funciona.
 */
export function TitleLens({ section }: { section: RefObject<HTMLElement> }) {
  const supported = useClientCheck(canvas2dAvailable);
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const root = section.current;
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    const title = root?.querySelector<HTMLElement>(".chapter__title");
    if (!supported || !root || !canvas || !ctx || !title) return;
    // Las palabras se dibujan juntas en esta máscara y se aplican de una vez (destination-in con
    // cada palabra por separado borraría las anteriores).
    const mask = document.createElement("canvas");
    const mctx = mask.getContext("2d");
    if (!mctx) return;
    title.classList.add("chapter__title--lens");
    const view = trackVisibility(root);
    const paper = getComputedStyle(document.documentElement).getPropertyValue("--paper").trim();

    const tick = () => {
      if (!view.visible) return;
      const host = canvas.offsetParent as HTMLElement | null;
      const box = title.getBoundingClientRect();
      const hostBox = host?.getBoundingClientRect() ?? box;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = Math.max(1, Math.round(box.width * dpr));
      const h = Math.max(1, Math.round(box.height * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      canvas.style.left = `${box.left - hostBox.left}px`;
      canvas.style.top = `${box.top - hostBox.top}px`;
      canvas.style.width = `${box.width}px`;
      canvas.style.height = `${box.height}px`;

      ctx.globalCompositeOperation = "source-over";
      ctx.clearRect(0, 0, w, h);
      const scene = root.querySelector<HTMLCanvasElement>(".chapter__scene canvas");
      const sceneBox = scene?.getBoundingClientRect();
      if (scene && sceneBox && sceneBox.width > 0 && scene.width > 0) {
        // El trozo de la escena que está detrás del título (con la respiración y el paralaje).
        const kx = scene.width / sceneBox.width;
        const ky = scene.height / sceneBox.height;
        ctx.filter = LENS_FILTER;
        ctx.drawImage(
          scene,
          (box.left - sceneBox.left) * kx,
          (box.top - sceneBox.top) * ky,
          box.width * kx,
          box.height * ky,
          0,
          0,
          w,
          h,
        );
        ctx.filter = "none";
        // Piso de luz: las letras siempre más claras que lo que las rodea, aunque detrás haya
        // una pared oscura.
        ctx.globalAlpha = LENS_FLOOR;
        ctx.fillStyle = paper;
        ctx.fillRect(0, 0, w, h);
        ctx.globalAlpha = 1;
      } else {
        // Sin escena todavía: letras de papel, como el título normal.
        ctx.fillStyle = paper;
        ctx.fillRect(0, 0, w, h);
      }

      // Recorte con las palabras en su posición real (incluye el revelado y el warp).
      if (mask.width !== w || mask.height !== h) {
        mask.width = w;
        mask.height = h;
      }
      mctx.clearRect(0, 0, w, h);
      const style = getComputedStyle(title);
      const size = parseFloat(style.fontSize) * dpr;
      mctx.font = `${style.fontWeight} ${size}px ${style.fontFamily}`;
      if ("letterSpacing" in mctx) {
        (mctx as CanvasRenderingContext2D & { letterSpacing: string }).letterSpacing =
          `${parseFloat(style.letterSpacing || "0") * dpr || 0}px`;
      }
      mctx.textBaseline = "alphabetic";
      mctx.fillStyle = "#000";
      title.querySelectorAll<HTMLElement>(".reveal__word").forEach((word) => {
        const text = word.textContent ?? "";
        const r = word.getBoundingClientRect();
        const m = mctx.measureText(text);
        const ascent = m.fontBoundingBoxAscent ?? size * 0.8;
        const descent = m.fontBoundingBoxDescent ?? size * 0.2;
        const halfLeading = (r.height * dpr - (ascent + descent)) / 2;
        // Cada palabra solo se pinta dentro de la máscara de su línea (como el título real
        // mientras entra); sin máscara, dentro del título.
        const clip = (word.closest(".reveal__line-mask") ?? title).getBoundingClientRect();
        mctx.save();
        mctx.beginPath();
        mctx.rect(
          (clip.left - box.left) * dpr,
          (clip.top - box.top) * dpr,
          clip.width * dpr,
          clip.height * dpr,
        );
        mctx.clip();
        mctx.fillText(
          text,
          (r.left - box.left) * dpr,
          (r.top - box.top) * dpr + halfLeading + ascent,
        );
        mctx.restore();
      });
      ctx.globalCompositeOperation = "destination-in";
      ctx.drawImage(mask, 0, 0);
      ctx.globalCompositeOperation = "source-over";
    };
    gsap.ticker.add(tick);

    return () => {
      gsap.ticker.remove(tick);
      view.stop();
      title.classList.remove("chapter__title--lens");
    };
  }, [section, supported]);

  if (!supported) return null;
  return <canvas ref={ref} className="title-lens" aria-hidden="true" />;
}
