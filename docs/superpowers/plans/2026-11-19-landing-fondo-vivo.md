# Fondo vivo y microinteracciones — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la página de presentación se sienta viva en reposo: degradado WebGL ondulante por capítulo, escenas que respiran con paralaje y microinteracciones con mouse y tacto.

**Architecture:** Un estado global del puntero (un solo juego de escuchadores pasivos) que leen piezas independientes en `gsap.ticker` (el reloj que ya sincroniza Lenis), sin re-renderizar React. El fondo es un `<canvas>` fijo con un *shader* en WebGL puro, detrás de `<main>`; se ve por las secciones sin video, que pasan a ser translúcidas.

**Tech Stack:** React 18, TypeScript estricto, GSAP (`gsap.ticker`), WebGL 1/2 puro, three.js/R3F solo en el teléfono existente, vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-11-19-landing-fondo-vivo-design.md`

## Global Constraints

- Rama única `feat/landing-fondo-vivo` desde `main` (guía 8.4); sin PR; *merge* `--no-ff`.
- Colores solo desde `src/styles/tokens.css` («Ningún color fuera de este archivo»): el *shader* los lee en tiempo de ejecución con `getComputedStyle(document.documentElement)`.
- Sin dependencias nuevas.
- `prefers-reduced-motion: reduce` (hook `useReducedMotion`): no se monta el *canvas*, no se suscribe nada a `gsap.ticker`, no hay animación CSS nueva.
- Escuchadores de puntero `passive: true` y sin `preventDefault`: el *scroll* táctil no se toca.
- Contraste del texto ≥ 4,5:1 en todas las secciones translúcidas.
- Antes de cada *commit*: `cd landing && npm test && npm run lint && npm run typecheck && npm run format:check`.
- Valores de partida del diseño: fondo a ⅓ de resolución; transición de paleta ~1 s; onda ~1,2 s; respiración escala 1,03 ↔ 1,06 en 14 s; paralaje máx. 1,5 % del ancho; imán radio 80 px y máx. 8 px; teléfono ± 0,12 rad; panel ± 4°; botón presionado escala 0,97.

## Review Focus

1. El mouse sale de la ventana o el dedo se levanta → todo vuelve a reposo (nada queda inclinado).
2. Arrastrar el dedo para hacer *scroll* en el celular → la página se desplaza normal (escuchadores pasivos).
3. El navegador pierde el contexto WebGL (celular en segundo plano) → el *canvas* se oculta, se ven los degradados CSS y no hay errores en consola.
4. Cambio de tamaño o giro del celular → el *canvas* se redimensiona sin deformarse.
5. La persona activa «reducir movimiento» con la página abierta → se detiene todo sin recargar.

---

### Task 1: Estado del puntero y matemáticas del movimiento

**Files:**
- Create: `landing/src/interaction/pointer.ts`, `landing/src/interaction/motion.ts`
- Test: `landing/src/interaction/pointer.test.ts`, `landing/src/interaction/motion.test.ts`

**Interfaces:**
- Produces:
  - `interface PointerState { x: number; y: number; active: boolean; touch: boolean; tap: { x: number; y: number; time: number } | null }` — `x` de −1 (izquierda) a 1 (derecha), `y` de −1 (arriba) a 1 (abajo); `time` en ms de `performance.now()`.
  - `const pointer: Readonly<PointerState>` (objeto mutable del módulo, solo lectura para el resto).
  - `startPointerTracking(): () => void` — con conteo de referencias: el primer llamado agrega los escuchadores en `window`, el último `stop` los quita.
  - `usePointerTracking(enabled: boolean): void` — hook que llama a `startPointerTracking` mientras `enabled`.
  - `normalize(clientX: number, clientY: number, width: number, height: number): { x: number; y: number }`
  - `damp(current: number, target: number, lambda: number, dtSeconds: number): number` — `target + (current − target)·e^(−lambda·dt)`.
  - `magnetOffset(dx: number, dy: number, radius = 80, max = 8): { x: number; y: number }`
  - `tiltFromPointer(x: number, y: number, max: number): { rx: number; ry: number }` — `rx = −y·max`, `ry = x·max`.

- [ ] **Step 1: Pruebas que fallan** — `motion.test.ts`:
  ```ts
  expect(normalize(0, 0, 800, 600)).toEqual({ x: -1, y: -1 });
  expect(normalize(400, 300, 800, 600)).toEqual({ x: 0, y: 0 });
  expect(normalize(900, 700, 800, 600)).toEqual({ x: 1, y: 1 }); // se recorta
  expect(damp(0, 10, 5, 0)).toBe(0);
  expect(damp(0, 10, 5, 10)).toBeCloseTo(10);
  expect(magnetOffset(40, 0)).toEqual({ x: 4, y: 0 });
  expect(magnetOffset(0, -80)).toEqual({ x: 0, y: -8 });
  expect(magnetOffset(100, 0)).toEqual({ x: 0, y: 0 });
  expect(tiltFromPointer(1, -1, 0.12)).toEqual({ rx: 0.12, ry: 0.12 });
  ```
  `pointer.test.ts` (eventos con `new PointerEvent` o `MouseEvent` despachados en `window`, `innerWidth` 800 × `innerHeight` 600):
  - `pointermove` de mouse en (400, 300) → `pointer` = `{ x: 0, y: 0, active: true, touch: false }`.
  - `pointerdown` táctil en (800, 0) → `active: true`, `touch: true`, `tap` con `x: 1, y: -1`; `pointerup` → `active: false`.
  - Mouse: `mouseout` de `document` con `relatedTarget: null` → `active: false` (Review Focus 1).
  - Los escuchadores se registran con `{ passive: true }` (espiar `window.addEventListener`) (Review Focus 2).
  - Dos `startPointerTracking()` y un solo `stop` → los escuchadores siguen; el segundo `stop` los quita.
- [ ] **Step 2:** `npm test` → FALLA (módulos inexistentes).
- [ ] **Step 3:** Implementar `motion.ts` y `pointer.ts` con las firmas de arriba.
- [ ] **Step 4:** `npm test` → PASA.
- [ ] **Step 5:** Commit `feat(landing): estado del puntero y funciones de movimiento`.

### Task 2: Fondo ambiental WebGL

**Files:**
- Create: `landing/src/ambient/palette.ts`, `landing/src/ambient/shader.ts`, `landing/src/ambient/AmbientBackground.tsx`, `landing/src/ambient/AmbientBackground.css`
- Modify: `landing/src/App.tsx` (montar `<AmbientBackground />` antes de `<main>`), `landing/src/chapters/SequenceChapter.tsx` (atributo `data-accent`), `landing/src/chapters/Reportar.tsx`, `landing/src/chapters/Panel.tsx`, `landing/src/components/DownloadSection.tsx`, `landing/src/components/SiteFooter.tsx` (atributos `data-accent` y `data-ambient`), y sus `.css` (fondo base translúcido)
- Test: `landing/src/ambient/palette.test.ts`, `landing/src/ambient/AmbientBackground.test.tsx`

**Interfaces:**
- Consumes: `pointer`, `usePointerTracking`, `damp` (Task 1); `useReducedMotion`; `isWebGLAvailable` (`src/three/isWebGLAvailable.ts`).
- Produces:
  - `type AmbientAccent = "amber" | "signal" | "repair" | "none"`
  - `type Rgb = readonly [number, number, number]` (0–1)
  - `hexToRgb(hex: string): Rgb`, `mixRgb(a: Rgb, b: Rgb, t: number): Rgb`
  - `paletteFor(accent: AmbientAccent, tokens: { night: Rgb; ink: Rgb; amber: Rgb; signal: Rgb; repair: Rgb }): readonly [Rgb, Rgb, Rgb, Rgb]` — `[night, ink, mix(night, A, 0.35), mix(night, A, 0.6)]` con `A` el color del acento; para `"none"`, `A = signal` con 0,15 y 0,25.
  - `dominantAccent(entries: readonly { accent: AmbientAccent; ratio: number }[]): AmbientAccent` — el de mayor `ratio`; `"none"` si la lista está vacía o todo es 0.
  - Atributos en el DOM: cada sección lleva `data-accent` (apertura `none`, problema `amber`, reportar `amber`, priorizar `signal`, panel `signal`, reparado `repair`, descarga `amber`, pie `none`); las translúcidas además `data-ambient="visible"`.
  - `<AmbientBackground />` — sin props.

- [ ] **Step 1: Pruebas que fallan** — `palette.test.ts`:
  ```ts
  const c = hexToRgb("#4c8dff");
  expect(c[0]).toBeCloseTo(0.298, 3); expect(c[1]).toBeCloseTo(0.553, 3); expect(c[2]).toBe(1);
  expect(mixRgb([0, 0, 0], [1, 1, 1], 0.25)).toEqual([0.25, 0.25, 0.25]);
  expect(paletteFor("repair", T)[3]).toEqual(mixRgb(T.night, T.repair, 0.6));
  expect(paletteFor("none", T)[2]).toEqual(mixRgb(T.night, T.signal, 0.15));
  expect(dominantAccent([{ accent: "amber", ratio: 0.2 }, { accent: "signal", ratio: 0.7 }])).toBe("signal");
  expect(dominantAccent([])).toBe("none");
  ```
  `AmbientBackground.test.tsx`:
  - Con `isWebGLAvailable` simulado en `false` → no renderiza `<canvas>`.
  - Con movimiento reducido (`matchMedia` en `reduce`) → no renderiza `<canvas>` aunque haya WebGL.
  - Con WebGL simulado (`getContext` devuelve un objeto falso con los métodos usados) → hay un `<canvas aria-hidden="true">`; al despachar `webglcontextlost` en él, recibe la clase `ambient--lost` (oculto) y no lanza (Review Focus 3).
  - `App` renderizado: todas las secciones de `<main>` tienen `data-accent`.
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar `palette.ts`.
- [ ] **Step 4:** Implementar `shader.ts`: exporta `VERTEX_SOURCE` (triángulo de pantalla completa) y `FRAGMENT_SOURCE` con uniformes `u_time` (s), `u_resolution` (vec2), `u_pointer` (vec2, −1…1, suavizado), `u_colors[4]` (vec3), `u_ripple` (vec3: x, y en −1…1 y edad en s; edad < 0 = sin onda). Aspecto: ruido suave (*simplex* o *value noise* de 2–3 octavas) desplazado muy despacio en diagonal que reparte los 4 colores en bandas anchas, con predominio de `u_colors[0]`; el puntero curva el campo en un radio amplio; la onda es un anillo que se expande y se apaga en 1,2 s. Precisión `mediump`.
- [ ] **Step 5:** Implementar `AmbientBackground.tsx`: si hay movimiento reducido o no hay WebGL, `null`. Si no, un `<canvas className="ambient" aria-hidden="true">` fijo (`position: fixed; inset: 0; z-index: -1; width: 100%; height: 100%`) con tamaño de *buffer* = tamaño CSS × `devicePixelRatio` / 3, recalculado en `resize` (Review Focus 4). Dibuja en `gsap.ticker` solo si `document.visibilityState === "visible"` y algún `[data-ambient="visible"]` está en pantalla (IntersectionObserver). Un segundo IntersectionObserver (umbrales 0…1 en pasos de 0,1) sobre `[data-accent]` alimenta `dominantAccent`; la paleta actual se acerca a la objetivo con `damp` (lambda 3 ≈ 1 s). `u_pointer` se acerca a `pointer` con `damp` (lambda 4) cuando `pointer.active`, y a (0, 0) si no. Un `pointer.tap` nuevo reinicia `u_ripple`. Los tokens se leen una vez al montar. `webglcontextlost` → `preventDefault`, clase `ambient--lost` (`display: none`) y se detiene el dibujo; `webglcontextrestored` → reinicializa y quita la clase. Usa `usePointerTracking(true)`.
- [ ] **Step 6:** Fondo translúcido: en `Reportar.css`, `Panel.css`, `DownloadSection.css` y `SiteFooter.css`, la capa base `var(--night)` pasa a `color-mix(in srgb, var(--night) 55%, transparent)`; los resplandores radiales se mantienen encima. Añadir `data-accent`/`data-ambient` a las secciones.
- [ ] **Step 7:** `npm test` → PASA; `npm run dev` y revisar a ojo en 1280 px y 390 px que el texto se lee (contraste ≥ 4,5:1 con la herramienta de contraste de DevTools sobre el punto más claro del degradado); ajustar el 55 % si no.
- [ ] **Step 8:** Commit `feat(landing): fondo ambiental WebGL que sigue el capítulo y el puntero`.

### Task 3: Escenas que respiran y paralaje

**Files:**
- Create: `landing/src/interaction/useDrift.ts`
- Modify: `landing/src/chapters/SequenceChapter.tsx`, `landing/src/chapters/SequenceChapter.css`
- Test: `landing/src/interaction/useDrift.test.tsx`

**Interfaces:**
- Consumes: `pointer`, `usePointerTracking`, `damp` (Task 1).
- Produces: `useDrift(ref: RefObject<HTMLElement>, options: { enabled: boolean; maxShift?: number /* fracción del ancho, 0.015 */ }): void` — en `gsap.ticker` escribe `transform: translate3d(x px, y px, 0)` en `ref.current` acercándose a `pointer.x/y · maxShift · ancho` (o a 0 si `!pointer.active`), lambda 4.

- [ ] **Step 1: Pruebas que fallan** — `useDrift.test.tsx` con `gsap.ticker.add`/`remove` espiados:
  - `enabled: false` → no llama a `gsap.ticker.add`.
  - `enabled: true` → llama a `add`; al desmontar, a `remove` con la misma función.
  - Con `pointer.active` falso, tras ejecutar el *callback* varias veces, el `transform` del elemento queda en `translate3d(0px, 0px, 0)` (Review Focus 1).
  - Al pasar `enabled` de `true` a `false` (movimiento reducido en vivo) → `remove` y el `transform` se limpia (Review Focus 5).
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar `useDrift`.
- [ ] **Step 4:** En `SequenceChapter.tsx`, dentro de `.chapter__scene` y alrededor de la secuencia/imagen, dos envoltorios: `.chapter__breath` (animación CSS `chapter-breath`: escala 1,03 → 1,06 → 1,03 en 14 s, `ease-in-out`, infinita) y dentro `.chapter__drift` (ref para `useDrift({ enabled: !still })`). `.chapter__shade` queda fuera de ambos. En `SequenceChapter.css`, la animación se anula dentro de `@media (prefers-reduced-motion: reduce)`.
- [ ] **Step 5:** `npm test` → PASA (incluye `chapters.test.tsx` existente).
- [ ] **Step 6:** Commit `feat(landing): escenas que respiran y paralaje con el puntero`.

### Task 4: Microinteracciones (imán, inclinación y presión)

**Files:**
- Create: `landing/src/interaction/useMagnetic.ts`, `landing/src/interaction/useTilt.ts`
- Modify: `landing/src/components/SiteHeader.tsx`, `landing/src/components/DownloadSection.tsx`, `landing/src/components/SiteHeader.css`, `landing/src/components/DownloadSection.css`, `landing/src/chapters/Panel.tsx`, `landing/src/chapters/Panel.css`, `landing/src/three/PhoneModel.tsx`
- Test: `landing/src/interaction/useMagnetic.test.tsx`, `landing/src/interaction/useTilt.test.tsx`

**Interfaces:**
- Consumes: `pointer`, `usePointerTracking`, `damp`, `magnetOffset`, `tiltFromPointer` (Task 1).
- Produces:
  - `useMagnetic(ref: RefObject<HTMLElement>, enabled: boolean): void` — activo solo si además `matchMedia("(hover: hover) and (pointer: fine)").matches`; usa `pointermove` en `window` (pasivo) con coordenadas en píxeles respecto al centro del elemento y `magnetOffset`; escribe `transform: translate(x px, y px)` suavizado en `gsap.ticker`; vuelve a 0 al salir del radio.
  - `useTilt(ref: RefObject<HTMLElement>, options: { enabled: boolean; maxDeg?: number /* 4 */ }): void` — escribe `transform: perspective(1200px) rotateX(rx deg) rotateY(ry deg)` con `tiltFromPointer(pointer.x, pointer.y, maxDeg)` suavizado; a 0 si `!pointer.active`.

- [ ] **Step 1: Pruebas que fallan**:
  - `useMagnetic`: con `(hover: hover) and (pointer: fine)` en `false` no se suscribe a `gsap.ticker`; en `true` sí, y un `pointermove` a 40 px a la derecha del centro de un elemento (`getBoundingClientRect` simulado) deja, tras varios *ticks*, `transform` cercano a `translate(4px, 0px)`; a 200 px vuelve a `translate(0px, 0px)`.
  - `useTilt`: `enabled: false` → sin suscripción; con `pointer.active` falso → `rotateX(0deg) rotateY(0deg)` tras varios *ticks* (Review Focus 1).
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar `useMagnetic` y `useTilt`.
- [ ] **Step 4:** Conectar:
  - `useMagnetic` en `.site-header__cta` y en `.download__cta` (este solo existe con `RELEASE`; si es `null`, en el elemento «Próximamente» no se aplica). CSS: `:active { transform: scale(0.97) }` con transición corta en ambos botones (presión táctil), anulada con movimiento reducido.
  - `useTilt` en un envoltorio nuevo `.panel__tilt` alrededor de `.panel__screen` (la transformación del *scroll* sigue en la figura); `enabled: !still`.
  - `PhoneModel`: un grupo exterior con `ref` y `useFrame` que suma la inclinación de `tiltFromPointer(pointer.x, pointer.y, 0.12)` suavizada con `damp` (a 0 si `!pointer.active`) a la rotación del *scroll* ya calculada; `usePointerTracking(true)` en `PhoneStage` solo cuando se monta el lienzo 3D.
- [ ] **Step 5:** `npm test` → PASA.
- [ ] **Step 6:** Commit `feat(landing): imán, inclinación y presión con mouse y tacto`.

### Task 5: Verificación, rendimiento y registro

**Files:**
- Modify: `docs/bitacora.md` (fila nueva), `CHANGELOG.md` (entrada de `landing/` en «Sin publicar»), `AGENTS.md` (punto de reanudación)

- [ ] **Step 1:** `cd landing && npm test && npm run lint && npm run typecheck && npm run format:check && npm run build` → todo en verde.
- [ ] **Step 2:** `npm run preview` y, con Chrome DevTools: escritorio 1280 px y celular emulado 390 × 844; revisar consola sin errores, Review Focus 1–5 a mano (salir de la ventana, *scroll* táctil, `WEBGL_lose_context.loseContext()` desde la consola, girar el dispositivo, emular `prefers-reduced-motion`).
- [ ] **Step 3:** Traza de rendimiento con CPU ×4 en móvil sobre Reportar y Descarga: el trabajo del *shader* por cuadro < 2 ms y sin cuadros largos nuevos; si no, bajar la resolución del *buffer* a ¼.
- [ ] **Step 4:** Lighthouse móvil: 100 en accesibilidad, buenas prácticas y SEO.
- [ ] **Step 5:** Registrar en la bitácora (decisión del responsable: enfoque A; decisiones menores del asistente de la sección 7 del diseño y cualquier ajuste de valores), CHANGELOG y AGENTS.md. Commit `docs: registrar el fondo vivo de la página de presentación`.
- [ ] **Step 6:** Subir la rama, esperar la CI en verde, *merge* `--no-ff` a `main`, subir y borrar la rama; comentario en Linear ARE-46.
