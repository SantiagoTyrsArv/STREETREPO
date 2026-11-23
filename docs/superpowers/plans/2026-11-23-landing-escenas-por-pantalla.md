# Escenas por pantalla y portada prerenderizada · Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que cada capítulo de `landing/` ocupe una pantalla y se reproduzca solo al llegar, con un imán de proximidad, y que la página llegue prerenderizada en el HTML (LCP < 2,5 s).

**Architecture:** Un hook nuevo, `useChapterPlayback`, sustituye a `useChapterProgress`. Entrega el mismo `progress` de 0 a 1, pero lo avanza en el tiempo (tween de GSAP) cuando el capítulo entra en la ventana, así que los hijos no cambian. `FrameSequence` carga sus cuadros solo cuando el capítulo está cerca y avisa cuando están listos. El imán usa `lenis/snap` en modo proximidad. El prerenderizado compila `src/entry-server.tsx` con `vite build --ssr`, inyecta el HTML en `dist/index.html`, y `main.tsx` hidrata.

**Tech Stack:** React 19, Vite, GSAP 3 (ScrollTrigger), Lenis 1.3.27 (`lenis/snap`), vitest + Testing Library, Node ≥ 22.18 para los scripts `.ts`.

**Spec:** `docs/superpowers/specs/2026-11-23-landing-escenas-por-pantalla-design.md`

## Global Constraints

- Rama: `feat/landing-escenas-por-pantalla`, creada desde `main`. Commits con Conventional Commits en español y cuerpo «qué, por qué y cómo se verificó» (guía 8.4).
- Sin dependencias nuevas (`lenis/snap` viene en `lenis` 1.3.27; `react-dom/server` en `react-dom`).
- CSP sin cambios: `script-src 'self'`, sin `<script>` en línea; `<noscript><style>` sí está permitido (`style-src 'unsafe-inline'`).
- Duraciones (ms): apertura 2500 · problema 3000 · reportar 6000 · priorizar 3500 · panel 2500 · reparado 3000.
- Disparo: cuando el capítulo ocupa ~40 % de la ventana (ScrollTrigger `start: "top 60%"`, `end: "bottom 40%"`), en cualquier dirección; una sola vez por carga.
- Movimiento reducido: sin Lenis, sin imán, sin reproducción; `progress = 1` (estado final), como hoy con `still`.
- Metas medidas: LCP < 2,5 s (DevTools, «Slow 4G», CPU ×4, 412×915 móvil, sin caché); CLS < 0,1; Lighthouse móvil ≥ 90 en accesibilidad y buenas prácticas; presupuesto de peso de la CI sin cambios.
- Textos de interfaz en español de Colombia; no se cambian textos, escenas ni orden.
- Al cerrar cada tarea: `npm test`, `npm run lint`, `npm run typecheck` y `npm run format:check` en `landing/` sin errores.

## Review Focus

1. **Llegar a un capítulo con red lenta:** el texto aparece igual y la escena se queda en `key.webp` o en el cuadro más cercano cargado; nunca queda en blanco. Prueba: `shouldStart` empieza a los `MAX_FRAME_WAIT_MS` aunque no esté `ready` (tarea 1); el texto del capítulo es visible tras la reproducción con `ready = false` (tarea 2).
2. **Saltar con «Saltar a la descarga» y volver arriba:** los capítulos saltados se reproducen al llegar a ellos, desde abajo. Prueba: el disparo por `onToggle` con `isActive` en dirección -1 inicia la reproducción (tarea 1).
3. **Volver a un capítulo ya visto:** se queda en su estado final, sin repetir. Prueba: un segundo `onToggle` activo no crea otro tween (tarea 1).
4. **Abrir la página sin JavaScript:** se leen los títulos y textos de todos los capítulos. Prueba: el `dist/index.html` compilado contiene los títulos y un `<noscript>` (tarea 4).
5. **Hidratación de la portada:** sin errores ni avisos de hidratación en la consola y sin salto visible. Prueba: `render()` en entorno `node` no falla y produce el mismo marcado que el primer render del cliente (tarea 4), más la verificación en el navegador (tarea 5).

---

### Task 1: Reproducción en el tiempo (`useChapterPlayback`)

**Files:**
- Create: `landing/src/scroll/playback.ts`
- Create: `landing/src/scroll/useChapterPlayback.ts`
- Test: `landing/src/scroll/playback.test.ts`, `landing/src/scroll/useChapterPlayback.test.tsx`

**Interfaces:**
- Produces:
  - `playback.ts`: `MAX_FRAME_WAIT_MS = 2500`; `TRIGGER_START = "top 60%"`; `TRIGGER_END = "bottom 40%"`; `NEAR_START = "top 250%"` (empieza a cargar cuando falta ~1,5 pantallas); `shouldStart(s: { triggered: boolean; ready: boolean; waitedMs: number }): boolean`.
  - `useChapterPlayback(ref: RefObject<HTMLElement | null>, o: { durationMs: number; enabled: boolean; ready: boolean; autoplay?: boolean }): { progress: number; near: boolean }`.
    - `enabled = false` → `{ progress: 1, near: false }` y no crea ScrollTriggers.
    - `autoplay = true` (portada) → `triggered` y `near` desde el montaje.
    - Si no, un ScrollTrigger `NEAR_START` pone `near = true` (una vez) y otro `TRIGGER_START`/`TRIGGER_END` con `onToggle` pone `triggered = true` la primera vez que `isActive`, en cualquier dirección.
    - Cuando `shouldStart` es verdadero, un único `gsap.to` lleva un objeto `{ value: 0 → 1 }` en `durationMs / 1000` s con `ease: "power2.out"` y publica `progress` en `onUpdate`. El tope de espera se cuenta desde `triggered` con un `setTimeout(MAX_FRAME_WAIT_MS)`.
    - Limpia los triggers, el temporizador y el tween al desmontar.

- [ ] **Step 1: Pruebas que fallan** (`playback.test.ts`):
  - `shouldStart({ triggered: false, ready: true, waitedMs: 0 })` → `false`
  - `shouldStart({ triggered: true, ready: true, waitedMs: 0 })` → `true`
  - `shouldStart({ triggered: true, ready: false, waitedMs: 2499 })` → `false`
  - `shouldStart({ triggered: true, ready: false, waitedMs: 2500 })` → `true`
- [ ] **Step 2: Pruebas del hook** (`useChapterPlayback.test.tsx`, con `vi.mock("./gsap")`, que captura los `ScrollTrigger.create(config)` y hace que `gsap.to(target, vars)` guarde `vars`; y `vi.useFakeTimers()`):
  - «con enabled false devuelve el estado final sin crear disparadores» → `progress === 1`, `create` no llamado.
  - «no avanza antes de entrar» → `progress === 0`, `gsap.to` no llamado.
  - «al entrar con los cuadros listos se reproduce en la duración del capítulo» → tras `onToggle({ isActive: true, direction: 1 })` con `ready: true`, `gsap.to` se llama una vez con `duration: 3` (para `durationMs: 3000`) y `ease: "power2.out"`; al invocar `vars.onUpdate` con `target.value = 1` → `progress === 1`.
  - «entrar desde abajo también reproduce» → `onToggle({ isActive: true, direction: -1 })` → `gsap.to` llamado.
  - «una sola reproducción por carga» → dos `onToggle` activos → `gsap.to` llamado una vez.
  - «sin cuadros, espera el tope y reproduce igual» → `ready: false`, `onToggle` activo; a los 2499 ms `gsap.to` no se ha llamado; a los 2500 ms sí.
  - «autoplay reproduce al montar» → `autoplay: true, ready: true` → `gsap.to` llamado sin `onToggle`; `near === true`.
  - «near se activa al acercarse» → el trigger con `start === NEAR_START` en su `onEnter` pone `near === true`.
- [ ] **Step 3:** `npx vitest run src/scroll` → FALLA (módulos inexistentes).
- [ ] **Step 4:** Implementar `playback.ts` y `useChapterPlayback.ts` según la interfaz.
- [ ] **Step 5:** `npx vitest run src/scroll` → PASA; lint, tipos y formato limpios.
- [ ] **Step 6: Commit** `feat(landing): reproducir los capítulos en el tiempo al entrar` (cuerpo con las pruebas ejecutadas).

### Task 2: Capítulos de una pantalla

**Files:**
- Modify: `landing/src/chapters/SequenceChapter.tsx` (config `pinLengthVh` → `durationMs`; quitar `VANISH_FROM` y el desvanecido; `autoplay` para la apertura; estado `framesReady`)
- Modify: `landing/src/sequence/FrameSequence.tsx` (props `load`, `onReady`)
- Modify: `landing/src/chapters/Reportar.tsx`, `landing/src/chapters/Panel.tsx` (quitar `PIN_LENGTH_VH`; usar el hook con 6000 y 2500 ms y `ready: true`)
- Delete: `landing/src/scroll/useChapterProgress.ts`
- Test: `landing/src/sequence/FrameSequence.test.tsx`, `landing/src/chapters/chapters.test.tsx` y las pruebas existentes que fallen por el cambio

**Interfaces:**
- Consumes: `useChapterPlayback` (tarea 1).
- Produces:
  - `SEQUENCE_CHAPTERS: { id: ChapterId; durationMs: number; accent; lens?; autoplay? }[]`, con las duraciones de las Global Constraints y `autoplay: true` solo en `apertura`.
  - `FrameSequence` gana `load: boolean` (el cargador se crea y arranca solo cuando `load` es `true`; el manifiesto se puede pedir antes) y `onReady?: () => void` (se llama una vez cuando `loader.loaded.size === manifest.frameCount`).
  - `SequenceChapter`: `const [framesReady, setFramesReady] = useState(false)`; `useChapterPlayback(ref, { durationMs, enabled: !still, ready: framesReady, autoplay })`; `<FrameSequence load={near} onReady={() => setFramesReady(true)} …/>`.

- [ ] **Step 1: Pruebas que fallan:**
  - `FrameSequence.test.tsx`: «no descarga cuadros mientras load es false» (con `fetch` simulado que devuelve un manifiesto de 3 cuadros, no se crea ninguna `Image` de cuadro); «avisa una vez cuando todos los cuadros están cargados» (`onReady` llamado una vez al cargar el tercero).
  - `chapters.test.tsx`: «los capítulos de escena duran lo del diseño» → `SEQUENCE_CHAPTERS.map(c => [c.id, c.durationMs])` igual a `[["apertura",2500],["problema",3000],["priorizar",3500],["reparado",3000]]`; «solo la apertura se reproduce al cargar»; «el texto queda visible al final» → con el hook simulado devolviendo `progress: 1`, el contenedor `.chapter__content` no tiene `opacity` 0.
- [ ] **Step 2:** `npm test` → las nuevas FALLAN.
- [ ] **Step 3:** Implementar los cambios de la lista de archivos. Las secciones mantienen `height: 100svh` (ya está en sus CSS). Al quitar el pin desaparece el espaciador de ScrollTrigger y la página se acorta sola.
- [ ] **Step 4:** `npm test`, lint, tipos y formato → PASA. Informar el número de pruebas, antes y después.
- [ ] **Step 5: Verificación en el navegador** (`npm run dev` y Chrome DevTools en 412×915 móvil): `document.documentElement.scrollHeight / innerHeight` ≤ 10; al bajar, cada escena corre sola y queda con el texto visible.
- [ ] **Step 6: Commit** `feat(landing): un capítulo por pantalla que se reproduce solo`.

### Task 3: Imán y «Pruébalo» compacta

**Files:**
- Modify: `landing/src/scroll/useSmoothScroll.ts` (crear `Snap` de `lenis/snap`)
- Modify: `landing/src/calculator/Calculator.css` (y `Calculator.tsx` solo si hace falta una clase)
- Test: `landing/src/scroll/useSmoothScroll.test.ts` (nuevo)

**Interfaces:**
- Produces: `SNAP_OPTIONS = { type: "proximity", distanceThreshold: "30%", debounce: 150 } as const` exportado desde `useSmoothScroll.ts`; los puntos de imán son `document.querySelectorAll("main > section")` con `align: "start"`, añadidos con `snap.addElement`. El `Snap` se destruye en la limpieza del efecto.

- [ ] **Step 1: Prueba que falla** (`vi.mock("lenis/snap")` y `vi.mock("lenis")`): «crea un imán de proximidad con un punto por capítulo» → con un `<main>` de 3 `<section>`, el constructor de `Snap` se llama con `SNAP_OPTIONS` y `addElement` 3 veces con `{ align: "start" }`; «sin animaciones no hay imán» → `useSmoothScroll(false)` no construye `Snap`; «al desmontar destruye el imán».
- [ ] **Step 2:** `npx vitest run src/scroll/useSmoothScroll.test.ts` → FALLA.
- [ ] **Step 3:** Implementar el imán.
- [ ] **Step 4:** Compactar `Calculator.css` hasta que `#prueba` mida ≤ `innerHeight` en 412×915 y en 1440×900 (hoy 1101 px en 412×915): menos margen vertical, opciones de severidad en una fila y bloque del resultado más compacto. Mantener áreas táctiles ≥ 44 px y contraste AA.
- [ ] **Step 5:** `npm test`, lint, tipos y formato → PASA. En el navegador: `#prueba` y `#descarga` miden ≤ `innerHeight` en 412×915 y en 1440×900; al soltar el scroll cerca de un capítulo, la página se acomoda en él; «Saltar a la descarga» y la barra de capítulos siguen saltando directo.
- [ ] **Step 6: Commit** `feat(landing): imán de proximidad y Pruébalo en una pantalla`.

### Task 4: Página prerenderizada

**Files:**
- Create: `landing/src/entry-server.tsx`, `landing/scripts/prerender.ts`
- Modify: `landing/src/main.tsx`, `landing/index.html` (`<noscript><style>`), `landing/package.json` (`build`), `landing/eslint.config.js` y `.gitignore` (ignorar `landing/dist-ssr/`)
- Modify (solo si la prueba SSR lo exige): componentes que lean `window`, `document` o `matchMedia` durante el render; mover esa lectura a un efecto con un valor inicial fijo (p. ej. `FrameSequence`: `useState<Resolution>("desktop")` y ajustar en un efecto)
- Test: `landing/src/entry-server.test.tsx`, `landing/scripts/prerender.test.ts`

**Interfaces:**
- Produces:
  - `entry-server.tsx`: `render(): string`, igual a `renderToString(<StrictMode><App /></StrictMode>)`.
  - `prerender.ts`: `injectApp(template: string, appHtml: string): string` sustituye exactamente `<div id="root"></div>` por `<div id="root">${appHtml}</div>`; lanza `Error("Falta <div id=\"root\"></div> en index.html")` si no está. El CLI lee `dist/index.html`, importa `dist-ssr/entry-server.js` y escribe el resultado.
  - `package.json`: `"build": "tsc --noEmit && vite build && vite build --ssr src/entry-server.tsx --outDir dist-ssr && node scripts/prerender.ts"`.
  - `main.tsx`: `hydrateRoot` si `#root` tiene hijos; si no, `createRoot` (en `npm run dev` el HTML viene vacío).

- [ ] **Step 1: Pruebas que fallan:**
  - `prerender.test.ts`: «inyecta la app en el contenedor» → `injectApp('<body><div id="root"></div></body>', '<main>x</main>')` igual a `'<body><div id="root"><main>x</main></div></body>'`; «falla si no hay contenedor vacío» → lanza con el mensaje de la interfaz.
  - `entry-server.test.tsx` (primera línea `// @vitest-environment node`): «renderiza sin navegador» → `render()` no lanza; «incluye la portada y todos los capítulos» → contiene `STREETREPO`, `COPY.apertura.title` y los títulos de problema, reportar, priorizar, prueba (calculadora), panel, reparado y descarga, tomados de `COPY`.
- [ ] **Step 2:** `npm test` → FALLAN.
- [ ] **Step 3:** Implementar. Corregir cada lectura del navegador durante el render que la prueba SSR revele.
- [ ] **Step 4:** Añadir a `index.html`, dentro de `<head>`, un `<noscript><style>` que muestre el estado final del texto (`.chapter__content` y el texto de `RevealText` visibles, con `opacity: 1 !important; transform: none !important`) y la portada sin máscara.
- [ ] **Step 5:** `npm run build` → `dist/index.html` contiene `STREETREPO`, los títulos de los capítulos y `<noscript>`; `node scripts/check-media-budget.ts` sigue en verde. `npm test`, lint, tipos y formato → PASA.
- [ ] **Step 6: Verificación en el navegador** (servir `dist/` con las cabeceras de `vercel.json`, como en la fila 124): sin errores de hidratación ni de CSP en la consola; con JavaScript desactivado se leen los textos de todos los capítulos.
- [ ] **Step 7: Commit** `perf(landing): prerenderizar la página al compilar`.

### Task 5: Medición, documentación e integración

**Files:**
- Modify: `landing/README.md`, `CHANGELOG.md` («Sin publicar»), `docs/bitacora.md` (fila nueva), `AGENTS.md` (estado de la página)

- [ ] **Step 1:** Subir la rama; cuando Vercel termine la vista previa, integrar a `main` (la vista previa pide sesión de Vercel; si no se puede abrir, medir en local sirviendo `dist/` con las cabeceras y luego en producción).
- [ ] **Step 2: Medición en producción** con Chrome DevTools (412×915 móvil, «Slow 4G», CPU ×4, sin caché): LCP < 2,5 s, CLS < 0,1; Lighthouse móvil ≥ 90 en accesibilidad y buenas prácticas; alto total ≤ 10 pantallas; recorrido con teclado (Tab por enlaces y controles, barra de capítulos, «Saltar a la descarga»). Si el LCP no baja de 2,5 s, informarlo con la cifra y la causa; no se da por cumplido.
- [ ] **Step 3:** Documentar: README de `landing/` (cómo funciona el recorrido, `dist-ssr/` y el prerenderizado), CHANGELOG, fila de la bitácora con las cifras medidas y el estado en `AGENTS.md`. Comentar en Linear ARE-46.
- [ ] **Step 4:** Verificar la CI en `main` y borrar la rama.
- [ ] **Step 5: Commit** `docs(landing): escenas por pantalla y prerenderizado`.
