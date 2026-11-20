# Textos vivos y secciones nuevas (entrega 1) — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entrega 1 del diseño: portada enmascarada con indicador de *scroll*, lupa en Reparado, títulos con revelado por líneas y *warp*, *variable proximity*, fórmula con contorno y descifrado, calculadora de urgencia, barra de progreso, Descarga en verde y espacio del video promocional.

**Architecture:** Efectos con los plugins de GSAP ya instalados (SplitText, ScrambleTextPlugin) y piezas propias que leen el estado del puntero existente (`src/interaction/pointer.ts`) en `gsap.ticker`, sin re-renderizar React. La lógica (calculadora, distancias, escalas, capítulo activo) vive en funciones puras probadas.

**Tech Stack:** React 18, TypeScript estricto, GSAP 3.15.1 (SplitText, ScrambleTextPlugin), Lenis, vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-11-20-landing-textos-reportar-video-design.md` (secciones 6.1–6.9)

## Global Constraints

- Rama `feat/landing-textos-vivos` desde `main`; sin PR; *merge* `--no-ff`.
- Sin librerías de animación nuevas. Únicas dependencias nuevas: `@fontsource-variable/archivo` y `@fontsource-variable/manrope` (5.3.0, versión exacta), que reemplazan a `@fontsource/archivo` y `@fontsource/manrope`.
- Colores solo desde `src/styles/tokens.css`.
- Movimiento reducido (`useReducedMotion`): ningún efecto; el texto se ve completo y quieto.
- Todo texto partido en letras o palabras conserva un único nombre accesible con el texto completo (envoltorio con `aria-label` o texto oculto y partes `aria-hidden="true"`).
- Contraste ≥ 4,5:1 (≥ 3:1 solo para texto ≥ 24 px).
- Escuchadores de puntero pasivos; el puntero se lee del módulo `pointer` (decisión 108).
- Textos de interfaz en español de Colombia, decimales con coma; todos en `src/content/copy.ts`.
- Antes de cada *commit*: `cd landing && npm test && npm run lint && npm run typecheck && npm run format:check`.

## Review Focus

1. El lector de pantalla lee cada título, antetítulo, párrafo y la fórmula una sola vez, completos, nunca letra por letra ni con caracteres del descifrado.
2. Al girar el celular o cambiar el ancho, los títulos partidos por líneas se vuelven a partir sin cortes raros ni texto encimado.
3. Con el dedo apoyado, *warp* y proximidad responden; al levantarlo vuelven exactamente al texto en reposo.
4. La calculadora, los puntos de progreso y el reproductor se usan por completo con teclado (Tab, flechas, Enter, Esc) y anuncian su estado.
5. Con `VIDEO = null` no aparece nada del video: ni botón, ni sección, ni punto en la barra.

---

### Task 1: Fuentes variables y *variable proximity*

**Files:**
- Modify: `landing/package.json`, `landing/src/main.tsx`, `landing/src/styles/tokens.css` (familias `"Archivo Variable"`, `"Manrope Variable"` con los respaldos actuales)
- Create: `landing/src/text/proximity.ts`, `landing/src/text/ProximityText.tsx`, `landing/src/text/ProximityText.css`
- Modify: `landing/src/chapters/SequenceChapter.tsx`, `Reportar.tsx`, `Panel.tsx`, `landing/src/components/SiteHeader.tsx`, `DownloadSection.tsx` (antetítulos, botones y *leads* con `ProximityText`)
- Test: `landing/src/text/proximity.test.ts`, `landing/src/text/ProximityText.test.tsx`

**Interfaces:**
- Consumes: `pointer`, `startPointerTracking`, `damp` (`src/interaction/`); `trackVisibility` (`src/interaction/visibility.ts`); `useReducedMotion`.
- Produces:
  - `falloff(distance: number, radius = 140): number` — 1 en 0, 0 desde `radius`, suave (`smoothstep` inverso).
  - `<ProximityText text={string} by="char" | "word" axes={{ wght: [number, number]; wdth?: [number, number] }} as?={ElementType} className?={string} />` — reposo = primer valor de cada eje; cerca del puntero (en píxeles de pantalla, con el centro de cada parte) hasta el segundo; escribe `font-variation-settings` por parte en `gsap.ticker`, solo si está visible y solo cuando cambia.

- [ ] **Step 1: Pruebas que fallan** — `proximity.test.ts`: `falloff(0)` = 1; `falloff(140)` = 0; `falloff(200)` = 0; `falloff(70)` entre 0,4 y 0,6; decreciente en 0, 35, 70, 105. `ProximityText.test.tsx`: con `by="char"` y texto «Descargar», `getByLabelText("Descargar")` existe y cada letra está en un nodo `aria-hidden`; con movimiento reducido se renderiza el texto plano sin partes; tras un `pointerdown` táctil sobre una parte (`getBoundingClientRect` simulado) y varios *ticks*, esa parte tiene `font-variation-settings` con `"wght"` mayor que el de reposo, y tras `pointerup` y varios *ticks* vuelve exactamente al de reposo (Review Focus 3).
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Cambiar dependencias (`npm uninstall @fontsource/archivo @fontsource/manrope && npm install --save-exact @fontsource-variable/archivo@5.3.0 @fontsource-variable/manrope@5.3.0`), importar `@fontsource-variable/archivo/wdth.css` y `@fontsource-variable/manrope/index.css` en `main.tsx` y actualizar las familias en `tokens.css`.
- [ ] **Step 4:** Implementar `proximity.ts` y `ProximityText` (las posiciones de las partes se miden al montar, con `resize` y con `trackVisibility`, no en cada cuadro).
- [ ] **Step 5:** Aplicar: antetítulos (`by="char"`, `wght` 700→900, `wdth` 100→115), botones «Descargar» del encabezado y de la sección (`by="char"`, `wght` 700→900 y 800→900), *leads* de capítulos, Reportar y Panel (`by="word"`, `wght` 400→600).
- [ ] **Step 6:** `npm test` → PASA (incluidas las pruebas existentes de capítulos, encabezado y descarga). Commit `feat(landing): fuentes variables y textos que se engrosan cerca del puntero`.

### Task 2: Títulos con revelado por líneas y *warp*

**Files:**
- Modify: `landing/src/components/RevealText.tsx`, `RevealText.css`
- Create: `landing/src/text/warp.ts`, `landing/src/text/useWarp.ts`
- Test: `landing/src/components/RevealText.test.tsx`, `landing/src/text/warp.test.ts`

**Interfaces:**
- Consumes: Task 1 (`falloff`); `pointer`, `damp`, `trackVisibility`.
- Produces:
  - `RevealText` mantiene sus props y suma `split?: "lines" | "words"` (por defecto `"lines"`; `"words"` es el comportamiento actual, que usará Reportar en la entrega 2).
  - `warpOffset(dx: number, dy: number, radius = 140, max = 6): { x: number; y: number; skew: number }` — empuja alejándose del punto: `x = −dx/|d| · max · falloff(|d|, radius)` (idem `y`), `skew` en grados = `x · 0,5`.
  - `useWarp(ref: RefObject<HTMLElement>, enabled: boolean): void` — aplica `warpOffset` a cada `.reveal__word` del título.

- [ ] **Step 1: Pruebas que fallan** — `warp.test.ts`: `warpOffset(0, 200)` = `{x:0, y:0, skew:0}`; `warpOffset(10, 0).x` < 0 y ≥ −6; `warpOffset(0, -10).y` > 0; simetría `warpOffset(10,0).x === -warpOffset(-10,0).x`. `RevealText.test.tsx`: con `split="lines"` el elemento `h2` tiene nombre accesible igual al texto completo (`getByRole("heading", { name: texto })`) y las partes son `aria-hidden` (Review Focus 1); con `still` no hay partes; con `progress` en `from` las líneas están ocultas (`transform` con `translateY(` positivo) y en `to` visibles (`translateY(0`).
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar con `SplitText.create(el, { type: "lines,words", mask: "lines", autoSplit: true, onSplit })`: en `onSplit` se recalculan las líneas (Review Focus 2); cada línea entra con `translateY(110% → 0)`, `rotate(4deg → 0)` y `blur(6px → 0)` según el tramo `from`–`to`. El `h2` conserva `aria-label`; SplitText marca las partes `aria-hidden`.
- [ ] **Step 4:** Implementar `warp.ts` y `useWarp`; activar en `RevealText` de títulos (`as` = `h1`/`h2`) cuando no hay movimiento reducido.
- [ ] **Step 5:** `npm test` → PASA. Revisar a ojo en `npm run dev` (escritorio y 390 px) que los títulos entran por líneas y que al girar se reparten bien. Commit `feat(landing): títulos que entran por líneas y se deforman con el puntero`.

### Task 3: Fórmula con contorno y descifrado

**Files:**
- Modify: `landing/src/chapters/Formula.tsx`, `Formula.css`
- Test: `landing/src/chapters/Formula.test.tsx`

**Interfaces:**
- Consumes: `COPY.formula` («U = 0,5·S + 0,3·F + 0,2·P»), `ScrambleTextPlugin` de GSAP.
- Produces: `Formula` con las mismas props (`progress`, `still`).

- [ ] **Step 1: Pruebas que fallan** — con movimiento reducido el texto visible es exactamente la fórmula, sin clase de contorno; sin movimiento reducido el párrafo tiene `aria-label` igual a la fórmula y el nodo animado es `aria-hidden` (Review Focus 1); con `progress` antes de `FORMULA_FROM` no se ha llamado a la animación de descifrado y al cruzarlo se llama una sola vez (espiar `gsap.to`); al terminar, el texto del nodo animado es la fórmula.
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Registrar `ScrambleTextPlugin`; al cruzar `FORMULA_FROM` (una vez por montaje), descifrar en 1,2 s con caracteres `"0123456789·=+SFPU"`. Contorno: `-webkit-text-stroke: 1px var(--paper)` con relleno transparente, y el relleno sube con un `background-clip: text` (degradado `--paper`) cuya altura sigue `progress` entre `FORMULA_FROM + 0,06` y `FORMULA_FROM + 0,2`. S, F y P en `--signal`.
- [ ] **Step 4:** `npm test` → PASA. Commit `feat(landing): fórmula que se descifra en contorno y se rellena`.

### Task 4: Portada enmascarada, lupa de Reparado e indicador de *scroll*

**Files:**
- Create: `landing/src/chapters/HeroMask.tsx`, `HeroMask.css`, `landing/src/chapters/heroMask.ts`, `landing/src/components/ScrollCue.tsx`, `ScrollCue.css`, `landing/src/chapters/TitleLens.tsx`, `TitleLens.css`
- Modify: `landing/src/chapters/SequenceChapter.tsx` (props `overlay?: (progress, still) => ReactNode`), `landing/src/App.tsx`, `landing/src/content/copy.ts` (`scrollCue: "Desliza"`)
- Test: `landing/src/chapters/heroMask.test.ts`, `HeroMask.test.tsx`, `landing/src/components/ScrollCue.test.tsx`, `landing/src/chapters/TitleLens.test.tsx`

**Interfaces:**
- Consumes: `SequenceChapter`, `useReducedMotion`, `COPY.reparado.title`.
- Produces:
  - `maskScale(progress: number, until = 0.3): number` — 1 en 0; ≥ 40 en `until` y después; creciente; *ease-in* (cúbica).
  - `<HeroMask progress={number} />` — capa `--night` con «STREET REPO» recortado, `aria-hidden`, escala `maskScale(progress)` desde el centro de la «O» de REPO; se quita del DOM al pasar `until`.
  - `<ScrollCue />` — «Desliza» con animación; se oculta para siempre al primer `scroll` con `scrollY > 40`.
  - `<TitleLens text={string} />` — capa `aria-hidden` sobre la escena de Reparado con el texto del título como máscara y la escena realzada dentro (`backdrop-filter: brightness(1.7) contrast(1.15) saturate(1.2)` recortado por el texto); si `CSS.supports("backdrop-filter", "blur(1px)")` es falso, no se monta.

- [ ] **Step 1: Pruebas que fallan** — `maskScale(0)` = 1; `maskScale(0.3)` ≥ 40; `maskScale(0.5)` = `maskScale(0.3)`; creciente en 0, 0,1, 0,2, 0,3. `HeroMask`: tiene `aria-hidden="true"`; con `progress` ≥ 0,3 no está en el DOM. `ScrollCue`: muestra «Desliza»; tras `scrollY = 100` y evento `scroll`, desaparece y no vuelve con `scrollY = 0`. `TitleLens`: `aria-hidden`; no se monta si `CSS.supports` devuelve `false`. En `SequenceChapter` de Apertura con movimiento reducido no hay `HeroMask` ni `ScrollCue` animado (estático).
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar. `HeroMask` y `ScrollCue` se pasan a Apertura por `overlay`; el `h1` «Cada calle cuenta.» y el texto aparecen tras la máscara (`introText` pasa a depender del progreso: visibles desde 0,3). `TitleLens` se pasa a Reparado por `overlay` (centrado sobre el título, mismo tamaño y posición que el `h2`).
- [ ] **Step 4:** `npm test` → PASA. Revisar a ojo en Chrome (escritorio y 390 px): la escena se ve dentro de «STREET REPO», el zoom atraviesa las letras, la lupa realza la escena dentro del título de Reparado. Commit `feat(landing): portada enmascarada, lupa en Reparado e indicador de scroll`.

### Task 5: Calculadora de urgencia «Pruébalo»

**Files:**
- Create: `landing/src/calculator/urgency.ts`, `landing/src/calculator/Calculator.tsx`, `Calculator.css`
- Modify: `landing/src/App.tsx` (después de Priorizar), `landing/src/content/copy.ts` (`calculadora`)
- Test: `landing/src/calculator/urgency.test.ts`, `landing/src/calculator/Calculator.test.tsx`

**Interfaces:**
- Produces:
  - `type Severity = "baja" | "media" | "alta"`; `type RoadKind = "principal" | "secundaria" | "terciaria" | "residencial" | "sin-via"`.
  - `severityScore(s: Severity): number` (3 / 6 / 10); `flowScore(r: RoadKind): number` (10 / 7 / 5 / 2 / 2); `proximityScore(distanceM: number): number` (distancia redondeada a centímetros; 10 si ≤ 100; `10·(500−d)/400` con dos decimales mitad hacia arriba; 0 si ≥ 500).
  - `urgency(scores: { s: number; f: number; p: number }, weights = { s: 0.5, f: 0.3, p: 0.2 }): number` — dos decimales, mitad hacia arriba, calculado en enteros (centésimas) para no arrastrar errores de coma flotante.
  - `formatDecimal(n: number): string` — coma decimal y dos cifras («8,70»).
  - `<Calculator />` — `section` con `id="prueba"`, `data-accent="signal"`, `data-ambient="visible"`.

- [ ] **Step 1: Pruebas que fallan** — tabla de la guía 8.3: `urgency({s:10,f:7,p:8})` = 8.7; `{6,10,10}` = 8; `{10,5,3.75}` = 7.25; `{6,5,10}` = 6.5; `{6,7,5}` = 6.1; `{6,2,0}` = 3.6. `proximityScore(100)` = 10; `proximityScore(500)` = 0; `proximityScore(350)` = 3.75; `proximityScore(600)` = 0; `proximityScore(100.004)` = 10. `formatDecimal(8.7)` = "8,70". `Calculator.test.tsx`: estado inicial S alta, vía secundaria, 180 m → muestra «8,70»; elegir «media», «principal» y 100 m → «8,00»; elegir «sin vía» muestra «Revisar vía»; el resultado está en un `role="status"`; los controles se manejan con teclado (radio de severidad con flechas, `select` de vía, `input type="range"` con flechas) (Review Focus 4).
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar `urgency.ts` y `Calculator` (desglose «0,5 · 10 + 0,3 · 7 + 0,2 · 8,00 = 8,70», barra 0–10, nota «Con los pesos por defecto; la Secretaría de Infraestructura puede ajustarlos»). Textos en `copy.ts`.
- [ ] **Step 4:** `npm test` → PASA. Commit `feat(landing): calculadora de urgencia con la fórmula real`.

### Task 6: Video promocional y Descarga en verde

**Files:**
- Create: `landing/src/config/video.ts`, `landing/src/video/VideoDialog.tsx`, `VideoDialog.css`, `landing/src/video/VideoSection.tsx`, `VideoSection.css`, `landing/src/video/VideoButton.tsx`
- Modify: `landing/src/scroll/useSmoothScroll.ts` (exporta `pauseSmoothScroll(): void` y `resumeSmoothScroll(): void`), `landing/src/App.tsx` (botón en Apertura vía `before`, sección antes de Descarga), `landing/src/components/DownloadSection.tsx` (`data-accent="repair"`), `landing/src/content/copy.ts` (`video`), `landing/src/App.test.tsx` (acento de descarga `repair`)
- Test: `landing/src/video/VideoDialog.test.tsx`, `landing/src/video/VideoSection.test.tsx`

**Interfaces:**
- Produces:
  - `interface PromoVideo { youtubeId: string; title: string; poster: string; aiGenerated: boolean }`; `export const VIDEO: PromoVideo | null = null`.
  - `<VideoDialog video={PromoVideo} open={boolean} onClose={() => void} />` — `<dialog>` modal; con `open` crea `<iframe src="https://www.youtube-nocookie.com/embed/{id}?autoplay=1&rel=0" title={video.title} allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen>`; al cerrar lo elimina, llama `resumeSmoothScroll` y devuelve el foco al botón que lo abrió.
  - `<VideoButton video={PromoVideo | null} />` y `<VideoSection video={PromoVideo | null} />` — devuelven `null` si `video` es `null`. La sección tiene `id="video"`, `data-accent="signal"`, `data-ambient="visible"`, la portada local (`<img>` con `width`/`height`) y, si `aiGenerated`, la etiqueta «Recreación generada con IA».

- [ ] **Step 1: Pruebas que fallan** — con `video={null}`, `VideoButton` y `VideoSection` no renderizan nada (Review Focus 5); `VideoSection` con video muestra el título y la etiqueta de IA; al pulsar reproducir se abre el diálogo con un `iframe` cuyo `src` empieza por `https://www.youtube-nocookie.com/embed/` (antes de pulsar no hay `iframe` en el documento); Esc cierra, el `iframe` desaparece y el foco vuelve al botón (Review Focus 4); se llamó a `pauseSmoothScroll` al abrir y a `resumeSmoothScroll` al cerrar. `App.test`: Descarga con `data-accent="repair"`. (Si jsdom no implementa `showModal`, simularlo en el `setup` de las pruebas.)
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar. Textos: botón «Ver el video», sección «Street Repo en 60 segundos», «Reproducir video», «Cerrar video», etiqueta «Recreación generada con IA».
- [ ] **Step 4:** `npm test` → PASA. Commit `feat(landing): espacio del video promocional y descarga en verde`.

### Task 7: Barra de progreso por capítulos

**Files:**
- Create: `landing/src/components/ChapterNav.tsx`, `ChapterNav.css`, `landing/src/components/chapters.ts`
- Modify: `landing/src/chapters/SequenceChapter.tsx` (`id={chapter.id}`), `Reportar.tsx` (`id="reportar"`), `Panel.tsx` (`id="panel"`), `landing/src/App.tsx`, `landing/src/content/copy.ts` (nombres de capítulo)
- Test: `landing/src/components/ChapterNav.test.tsx`

**Interfaces:**
- Consumes: Task 5 (`id="prueba"`); Task 6 (`VIDEO` para incluir o no «video»).
- Produces:
  - `CHAPTER_IDS` en orden: `apertura, problema, reportar, priorizar, prueba, panel, reparado, video, descarga`.
  - `pickActive(entries: readonly { id: string; top: number; height: number }[], viewportHeight: number): string | null` — el capítulo que contiene la línea media de la ventana.
  - `<ChapterNav chapters={readonly { id: string; label: string }[]} />` — `nav aria-label="Capítulos"`; en ≥ 768 px, enlaces `href="#id"` con `aria-current="true"` en el activo y el nombre visible al pasar el mouse o con foco; en < 768 px, una línea fina `aria-hidden` con el avance total.

- [ ] **Step 1: Pruebas que fallan** — `pickActive` elige el que contiene la línea media; `null` con lista vacía. `ChapterNav`: hay un enlace por capítulo con su `href`; el activo tiene `aria-current`; sin `VIDEO` no aparece «video» (Review Focus 5); los enlaces son alcanzables con Tab.
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar. El activo se recalcula en `scroll` (pasivo, con `requestAnimationFrame`). Al hacer clic, desplazar con Lenis si existe (`scrollTo` de la instancia) o con el ancla nativa.
- [ ] **Step 4:** `npm test` → PASA. Commit `feat(landing): barra de progreso por capítulos`.

### Task 8: Verificación, registro e integración

**Files:**
- Modify: `docs/bitacora.md` (fila nueva), `CHANGELOG.md`, `AGENTS.md` (punto de reanudación), `landing/media/README.md` (cómo publicar el video: ID de YouTube, portada en `public/media/video/poster.webp`, `aiGenerated`)

- [ ] **Step 1:** `cd landing && npm test && npm run lint && npm run typecheck && npm run format:check && npm run build` → todo en verde.
- [ ] **Step 2:** `npm run preview` y Chrome DevTools, en escritorio 1280 px y celular 390 × 844: consola sin errores; Review Focus 1–5 a mano (lector: árbol de accesibilidad de DevTools; giro del celular; dedo apoyado y soltado; teclado en calculadora, barra y diálogo; `VIDEO = null`). Prueba del diálogo con un `VIDEO` temporal en local (sin *commit*).
- [ ] **Step 3:** Fluidez con CPU ×4 en celular emulado: sin cuadros > 50 ms en Apertura (zoom), Priorizar (fórmula), Pruébalo y Reparado (lupa). Contraste medido de los textos nuevos. Lighthouse móvil 100 en accesibilidad y buenas prácticas.
- [ ] **Step 4:** Registrar (bitácora, CHANGELOG, AGENTS.md, `media/README.md`). Commit `docs: registrar los textos vivos y las secciones nuevas`.
- [ ] **Step 5:** Revisión final de la rama completa; correcciones con prueba que falle primero; subir la rama, CI en verde, *merge* `--no-ff`, borrar la rama, comentario en Linear ARE-46.
