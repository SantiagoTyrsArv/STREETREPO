import gsap from "gsap";
import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { damp } from "../interaction/motion";
import { pointer, usePointerTracking } from "../interaction/pointer";
import { useClientCheck } from "../lib/useClientCheck";
import { isWebGLAvailable } from "../three/isWebGLAvailable";
import {
  dominantAccent,
  hexToRgb,
  paletteFor,
  type AmbientAccent,
  type AmbientTokens,
  type Rgb,
} from "./palette";
import { advanceTime } from "./clock";
import { FRAGMENT_SOURCE, VERTEX_SOURCE } from "./shader";
import "./AmbientBackground.css";

/** El degradado no tiene detalle fino: se dibuja a ⅓ de la resolución y se escala con CSS. */
const RESOLUTION_SCALE = 1 / 3;
/** Suavizados (1/s): paleta ≈ 1 s, puntero ágil pero sin tirones. */
const PALETTE_LAMBDA = 3;
const POINTER_LAMBDA = 4;
const STRENGTH_LAMBDA = 2.5;
/** Duración de la onda de un toque, en s (igual que en el shader). */
const RIPPLE_SECONDS = 1.2;
/** Parte del degradado que atraviesa el velo de noche (el resto es `--night`): contraste del texto. */
const VEIL = 0.5;
const ACCENTS: readonly AmbientAccent[] = ["amber", "signal", "repair", "none"];

function readTokens(): AmbientTokens {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string): Rgb => {
    try {
      return hexToRgb(style.getPropertyValue(name));
    } catch {
      return [0, 0, 0];
    }
  };
  return {
    night: read("--night"),
    ink: read("--ink"),
    amber: read("--amber"),
    signal: read("--signal"),
    repair: read("--repair"),
  };
}

function compile(gl: WebGLRenderingContext, type: number, source: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    gl.deleteShader(shader);
    return null;
  }
  return shader;
}

interface Scene {
  gl: WebGLRenderingContext;
  uniforms: Record<
    "time" | "resolution" | "pointer" | "strength" | "ripple" | "colors" | "veil",
    WebGLUniformLocation | null
  >;
}

function createScene(canvas: HTMLCanvasElement): Scene | null {
  const gl = canvas.getContext("webgl", {
    alpha: false,
    antialias: false,
    depth: false,
    powerPreference: "low-power",
    premultipliedAlpha: false,
  });
  if (!gl) return null;
  const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX_SOURCE);
  const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SOURCE);
  const program = gl.createProgram();
  if (!vertex || !fragment || !program) return null;
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
  gl.useProgram(program);

  // Un triángulo más grande que la pantalla: sin costura en la diagonal.
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, "a_position");
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

  const at = (name: string) => gl.getUniformLocation(program, name);
  return {
    gl,
    uniforms: {
      time: at("u_time"),
      resolution: at("u_resolution"),
      pointer: at("u_pointer"),
      strength: at("u_strength"),
      ripple: at("u_ripple"),
      colors: at("u_colors"),
      veil: at("u_veil"),
    },
  };
}

/**
 * Fondo vivo de la página: un degradado de seda en WebGL, fijo detrás del contenido, que toma el
 * acento del capítulo visible y responde al mouse y al dedo. Se ve por las secciones sin video
 * (`data-ambient="visible"`); sin WebGL o con movimiento reducido no se monta y quedan los
 * degradados CSS de cada sección.
 */
export function AmbientBackground() {
  const still = useReducedMotion();
  const webgl = useClientCheck(isWebGLAvailable);
  const enabled = webgl && !still;
  usePointerTracking(enabled);
  const ref = useRef<HTMLCanvasElement>(null);
  const [lost, setLost] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const canvas = ref.current;
    if (!enabled || !canvas) return;

    let scene = createScene(canvas);
    let contextLost = false;
    const tokens = readTokens();
    const palettes = Object.fromEntries(
      ACCENTS.map((a) => [a, paletteFor(a, tokens).flatMap((c) => [...c])]),
    ) as Record<AmbientAccent, number[]>;
    let target: AmbientAccent = "none";
    const colors = new Float32Array(palettes.none);
    const smooth = { x: 0, y: 0, strength: 0 };
    const ripple = { x: 0, y: 0, start: -Infinity, seen: -1 };
    let seeThroughVisible = 0;
    let firstFrame = true;
    let clock = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(window.innerWidth * dpr * RESOLUTION_SCALE));
      canvas.height = Math.max(1, Math.round(window.innerHeight * dpr * RESOLUTION_SCALE));
      scene?.gl.viewport(0, 0, canvas.width, canvas.height);
    };
    resize();
    window.addEventListener("resize", resize, { passive: true });

    // Qué secciones translúcidas están en pantalla y qué acento domina la vista.
    const ratios = new Map<Element, number>();
    const accentObserver = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) ratios.set(entry.target, entry.intersectionRatio);
        target = dominantAccent(
          [...ratios].map(([el, ratio]) => ({
            accent: (el.getAttribute("data-accent") as AmbientAccent | null) ?? "none",
            ratio: ratio * (el as HTMLElement).offsetHeight,
          })),
        );
      },
      { threshold: Array.from({ length: 11 }, (_, i) => i / 10) },
    );
    const visibleSet = new Set<Element>();
    const seeThroughObserver = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) visibleSet.add(entry.target);
        else visibleSet.delete(entry.target);
      }
      seeThroughVisible = visibleSet.size;
    });
    document.querySelectorAll("[data-accent]").forEach((el) => accentObserver.observe(el));
    document
      .querySelectorAll('[data-ambient="visible"]')
      .forEach((el) => seeThroughObserver.observe(el));

    const tick = (_time: number, deltaMs: number) => {
      if (!scene || contextLost || document.visibilityState !== "visible") return;
      if (seeThroughVisible === 0 && !firstFrame) return;
      const dt = Math.min(deltaMs / 1000, 0.1);
      const now = performance.now();

      const goal = palettes[target];
      for (let i = 0; i < colors.length; i++) {
        colors[i] = damp(colors[i] as number, goal[i] as number, PALETTE_LAMBDA, dt);
      }
      const active = pointer.active ? 1 : 0;
      smooth.x = damp(smooth.x, active ? pointer.x : 0, POINTER_LAMBDA, dt);
      smooth.y = damp(smooth.y, active ? pointer.y : 0, POINTER_LAMBDA, dt);
      const energy = active * Math.min(1, 0.55 + pointer.speed * 0.6);
      smooth.strength = damp(smooth.strength, energy, STRENGTH_LAMBDA, dt);
      if (pointer.tap && pointer.tap.time !== ripple.seen) {
        ripple.seen = pointer.tap.time;
        ripple.x = pointer.tap.x;
        ripple.y = pointer.tap.y;
        ripple.start = now;
      }
      const age = (now - ripple.start) / 1000;

      const { gl, uniforms } = scene;
      clock = advanceTime(clock, dt);
      gl.uniform1f(uniforms.time, clock);
      gl.uniform2f(uniforms.resolution, canvas.width, canvas.height);
      gl.uniform2f(uniforms.pointer, smooth.x, smooth.y);
      gl.uniform1f(uniforms.strength, smooth.strength);
      gl.uniform3f(uniforms.ripple, ripple.x, ripple.y, age <= RIPPLE_SECONDS ? age : -1);
      gl.uniform3fv(uniforms.colors, colors);
      gl.uniform1f(uniforms.veil, VEIL);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (firstFrame) {
        firstFrame = false;
        setReady(true);
      }
    };
    gsap.ticker.add(tick);

    const onLost = (event: Event) => {
      event.preventDefault();
      contextLost = true;
      setLost(true);
    };
    const onRestored = () => {
      scene = createScene(canvas);
      resize();
      contextLost = false;
      setLost(false);
    };
    canvas.addEventListener("webglcontextlost", onLost);
    canvas.addEventListener("webglcontextrestored", onRestored);

    return () => {
      gsap.ticker.remove(tick);
      window.removeEventListener("resize", resize);
      accentObserver.disconnect();
      seeThroughObserver.disconnect();
      canvas.removeEventListener("webglcontextlost", onLost);
      canvas.removeEventListener("webglcontextrestored", onRestored);
    };
  }, [enabled]);

  if (!enabled) return null;
  const classes = ["ambient", ready && "ambient--ready", lost && "ambient--lost"].filter(Boolean);
  return <canvas ref={ref} className={classes.join(" ")} aria-hidden="true" />;
}
