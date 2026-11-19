# Página de presentación y descarga — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** construir y desplegar en Vercel una página editorial e inmersiva que presente Street Repo
al jurado con un recorrido guiado por el *scroll* y deje preparada la descarga del APK.

**Architecture:** proyecto estático `landing/` (Vite + React + TS) en el monorrepo. Las escenas son
videos de Higgsfield convertidos en secuencias de cuadros WebP que un `<canvas>` dibuja según el
progreso del *scroll* (GSAP ScrollTrigger + Lenis); un teléfono 3D (React Three Fiber) muestra
capturas reales de la app. Sin servidor, sin analítica.

**Tech Stack:** Node 22, Vite 8, React 18.3, TypeScript 5.9 `strict`, GSAP 3 + ScrollTrigger,
Lenis, three + @react-three/fiber 8 + @react-three/drei 9, @fontsource (Archivo, Manrope,
Instrument Serif), qrcode, vitest + Testing Library, ffmpeg (local), Higgsfield MCP, Vercel.

**Spec:** `docs/superpowers/specs/2026-11-19-landing-descarga-apk-design.md` (bitácora, fila 99).

## Global Constraints

- Todo texto visible en **español de Colombia**; decimales con coma (`0,5·S`); identificadores en inglés.
- Tokens exactos: `--night #0A0E13`, `--ink #1B2430`, `--paper #F5F3EE`, `--mist #8A94A3`,
  `--amber #F5B800`, `--signal #4C8DFF`, `--repair #3DD68C`. Ningún color suelto fuera de `tokens.css`.
- Un acento dominante por escena; ámbar solo para el problema y la llamada a la acción.
- **Ninguna cifra de uso inventada.** Solo valores reales del proyecto (fórmula U, 25 m, 30 m, 100 m, 500 m).
- Imágenes generadas = ilustración; el pie dice «Imágenes y videos ilustrativos generados con IA».
- Capturas de la app y del panel solo con datos de `seed-demo`; nunca los reportes reales del responsable.
- Sin peticiones a terceros en tiempo de ejecución (fuentes y medios desde el propio dominio).
- WCAG 2.2 AA: contraste de texto ≥ 4,5:1, foco visible, teclado, `prefers-reduced-motion` respetado.
- Presupuesto de medios: ≤ 6 MB antes del primer capítulo interactivo; ≤ 45 MB total escritorio; ≤ 25 MB total móvil.
- Dependencias con **versión exacta** (`npm install -E`), `package-lock.json` versionado, `npm audit --audit-level=high` limpio.
- Flujo de la guía 8.4: una rama por tarea desde `main`, Conventional Commits con cuerpo (qué, por qué,
  cómo se verificó), `git merge --no-ff` a `main` sin PR, borrar la rama. Al empezar y terminar cada
  tarea: fila en `docs/bitacora.md` (en la misma rama) y estado en Linear (proyecto «Street Repo»).
- Los originales de Higgsfield **no** entran al repositorio; solo los medios optimizados en `landing/public/media/`.

## Review Focus

1. **Red lenta (4G del jurado):** al llegar a un capítulo cuyos cuadros aún no cargan, el canvas muestra el cuadro cargado más cercano, nunca un lienzo vacío → prueba `nearestLoaded` (Tarea 5).
2. **`prefers-reduced-motion`:** sin *scroll* suave ni secuencias; cada capítulo muestra su cuadro clave fijo y todo el texto → prueba en Tarea 6.
3. **Sin WebGL o GPU débil:** el teléfono 3D cae a una imagen fija con su texto alternativo, sin romper la página → prueba `PhoneStage` (Tarea 7).
4. **Celular girado o ventana redimensionada:** se elige la resolución correcta y el canvas se redimensiona sin deformar → pruebas `pickResolution` y `coverRect` (Tarea 5).
5. **Ir directo a la descarga** (enlace «Descargar» del encabezado, teclado, salto de contenido): la sección es alcanzable y enfocable sin recorrer todo el *scroll* → prueba en Tarea 8.

---

### Task 1: Andamiaje de `landing/`, tokens, fuentes y CI

Rama: `feat/landing-andamiaje`.

**Files:**
- Create: `landing/package.json`, `landing/index.html`, `landing/vite.config.ts`, `landing/tsconfig.json`,
  `landing/eslint.config.js`, `landing/.prettierrc`, `landing/src/main.tsx`, `landing/src/App.tsx`,
  `landing/src/styles/tokens.css`, `landing/src/styles/global.css`, `landing/src/lib/contrast.ts`,
  `landing/src/test/setup.ts`, `landing/README.md`
- Test: `landing/src/lib/contrast.test.ts`, `landing/src/App.test.tsx`
- Modify: `.github/workflows/ci.yml` (nuevo trabajo `landing`), `.gitignore` (`landing/dist`, `landing/media/originals/`)

**Interfaces:**
- Produces: `contrastRatio(a: string, b: string): number` (hex `#RRGGBB`, fórmula WCAG de luminancia
  relativa); variables CSS de los tokens; `<App />` con `<main id="contenido">`.

- [ ] **Step 1:** Copiar de `admin-web` la configuración de `eslint.config.js` (incluidas las reglas
  `no-restricted-syntax` y `no-restricted-globals`), `tsconfig.json` (`strict`), `vite.config.ts`
  (jsdom, `src/**/*.test.{ts,tsx}`) y los mismos scripts de `package.json` (`dev`, `build`
  = `tsc --noEmit && vite build`, `lint`, `format:check`, `typecheck`, `test`), con nombre
  `street-repo-landing`, versión `0.1.0`, `engines.node >=22.12` y las mismas versiones de las
  herramientas comunes.
- [ ] **Step 2: Prueba que falla** — `contrast.test.ts`:
  ```ts
  expect(contrastRatio("#000000", "#FFFFFF")).toBeCloseTo(21, 1);
  for (const [fg, bg] of [["#F5F3EE","#0A0E13"],["#8A94A3","#0A0E13"],["#F5B800","#0A0E13"],
    ["#4C8DFF","#0A0E13"],["#3DD68C","#0A0E13"],["#1B2430","#F5F3EE"]])
    expect(contrastRatio(fg, bg)).toBeGreaterThanOrEqual(4.5);
  ```
  y `App.test.tsx`: `render(<App />)` tiene `getByRole("main")`.
- [ ] **Step 3:** `npm test` → FALLA (no existe `contrastRatio` ni `App`).
- [ ] **Step 4:** Implementar `contrastRatio`, `tokens.css` con los siete tokens de las Global
  Constraints y los tamaños tipográficos (`--fs-display: clamp(3.5rem, 11vw, 11rem)` y una escala
  hasta `--fs-small`), `global.css` (fondo `--night`, texto `--paper`, `:focus-visible` con anillo
  `--amber` de 2 px), fuentes `@fontsource/archivo` (700, 800), `@fontsource/manrope` (400–600) y
  `@fontsource/instrument-serif` (400, normal e itálica) importadas en `main.tsx`. `index.html` con
  `lang="es-CO"`, `<title>Street Repo — Reporta. Prioriza. Repara.</title>` y `meta description`.
- [ ] **Step 5:** `npm test`, `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm run build` → todo en verde.
- [ ] **Step 6:** Añadir a `ci.yml` el trabajo `landing`, igual al de `admin-web` (mismas acciones
  fijadas por SHA, Node 22, `npm ci`, lint, formato, tipos, pruebas, `npm audit --audit-level=high`,
  compilar) con `working-directory: landing`, más el paso de presupuesto de medios que añade la Tarea 9.
- [ ] **Step 7:** Commit `feat(landing): andamiaje con tokens, fuentes y CI`, subir la rama y comprobar la CI en verde.

### Task 2: Despliegue en Vercel con cabeceras de seguridad

Rama: `chore/landing-vercel`.

**Files:**
- Create: `landing/vercel.json`
- Modify: `landing/README.md` (sección «Despliegue»)

- [ ] **Step 1:** `vercel.json`: `"cleanUrls": true` y `headers` para `/(.*)`:
  `Content-Security-Policy: default-src 'self'; img-src 'self' data: blob:; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; worker-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`,
  `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy: camera=(), microphone=(), geolocation=()`; y para `/media/(.*)` y
  `/assets/(.*)`: `Cache-Control: public, max-age=31536000, immutable`.
- [ ] **Step 2 (responsable):** en Vercel, *Add New → Project*, importar `SantiagoTyrsArv/STREETREPO`,
  *Root Directory* `landing`, *Framework* Vite, *Output* `dist`, *Ignored Build Step*
  `git diff --quiet HEAD^ HEAD -- .` (solo compila si cambia `landing/`). El asistente guía y no toca la cuenta.
- [ ] **Step 3:** Subir la rama y abrir la URL de vista previa. `curl -sI <url>` muestra las cinco
  cabeceras de seguridad; la página carga sin errores de CSP en la consola (Chrome DevTools MCP).
- [ ] **Step 4:** Commit `chore(landing): despliegue en Vercel con cabeceras de seguridad`; integrar a `main` y verificar el despliegue de producción.

### Task 3: Marca — símbolo y logotipo

Rama: `feat/landing-marca`.

**Files:**
- Create: `landing/media/brand-brief.md`, `landing/src/assets/brand/symbol.svg`,
  `landing/src/assets/brand/wordmark.svg`, `landing/src/components/Logo.tsx`,
  `landing/public/favicon.svg`, `landing/public/apple-touch-icon.png`
- Test: `landing/src/components/Logo.test.tsx`

**Interfaces:**
- Produces: `<Logo variant="horizontal" | "stacked" | "symbol" tone="light" | "dark" | "mono" />`
  con `role="img"` y `aria-label="Street Repo"`.

- [ ] **Step 1:** Escribir `brand-brief.md`: valores (cívico, preciso, confiable, de Pasto), ideas
  (punto de ubicación, grieta o bache estilizado, señal vial, monograma S/R), reglas (geometría
  simple, un solo color, legible a 24 px, sin texto dentro del símbolo, sin degradados), paleta de
  las Global Constraints.
- [ ] **Step 2:** Higgsfield: `generate_image_batch` con al menos 4 direcciones × 4 variantes
  (fondo plano, vista frontal, alto contraste), con el mejor modelo de imagen según `models_explore`.
  Presentar al responsable una hoja de contacto con las 16 y pedirle que elija 1–3; repetir rondas
  refinando las elegidas hasta que apruebe **una**.
- [ ] **Step 3:** Redibujar la elegida a mano como `symbol.svg` (trazos en retícula de 24, sin
  imágenes incrustadas, `viewBox="0 0 24 24"`) y componer `wordmark.svg` (símbolo + «Street Repo»
  en Archivo 800 convertido a trazos, interletraje ajustado). Mostrar al responsable y ajustar.
- [ ] **Step 4: Prueba que falla** — `Logo.test.tsx`: para las tres variantes,
  `getByRole("img", { name: "Street Repo" })` existe; `tone="mono"` usa `currentColor`.
- [ ] **Step 5:** Implementar `Logo.tsx` (SVG en línea, colores por token). `npm test` → PASA.
- [ ] **Step 6:** `favicon.svg` desde el símbolo y `apple-touch-icon.png` de 180 px; enlazarlos en `index.html`.
- [ ] **Step 7:** Hoja de uso (área de reserva = alto de la «S», tamaño mínimo 24 px, versiones) en
  `landing/media/README.md`. Commit `feat(landing): símbolo y logotipo de Street Repo`; integrar.

### Task 4: Biblia de estilo, cuadros clave y videos de las escenas

Rama: `feat/landing-escenas`. Es la tarea más larga: el responsable aprueba cada cuadro clave y cada video.

**Files:**
- Create: `landing/media/style-bible.md`, `landing/media/README.md` (inventario), `landing/scripts/build-sequences.sh`,
  `landing/public/media/<chapter>/{desktop,mobile}/frame_0001.webp…`, `landing/public/media/<chapter>/manifest.json`,
  `landing/public/media/<chapter>/key.webp`
- Originales (fuera de git): `landing/media/originals/`

**Interfaces:**
- Produces: por cada `ChapterId` de secuencia (`"apertura" | "problema" | "priorizar" | "reparado"`)
  un `manifest.json` con la forma `SequenceManifest` (Tarea 5) y un `key.webp` (cuadro clave, también respaldo y póster).

- [ ] **Step 1:** Ejecutar `get_workflow_instructions` (sin argumento) de Higgsfield y seguir su
  flujo para videos de varios pasos. Escribir `style-bible.md`: formato 16:9 (escritorio) y 9:16
  (móvil) por escena; luz nocturna fría con un acento por escena según la sección 6 del diseño;
  lente 35 mm, poca profundidad de campo, grano fílmico sutil, sin personas reconocibles, sin
  texto ni placas legibles, arquitectura andina de Pasto, el Galeras al fondo en la apertura.
- [ ] **Step 2:** Por cada escena, generar **cuadro inicial y final** (imagen) con la biblia como
  prefijo común e imágenes de referencia entre escenas para que «problema» (1) y «reparado» (5)
  sean la **misma calle** (el final de 5 parte del inicial de 1). Varias variantes por cuadro.
- [ ] **Step 3 (responsable):** aprobar los cuadros clave de las cuatro escenas antes de generar video.
- [ ] **Step 4:** Generar cada video imagen → video (cuadro inicial y final) con el mejor modelo
  de video según `models_explore`, 6–10 s, cámara lenta continua (dolly, descenso), sin cortes;
  esperar con `jobs_wait`; reescalar con `upscale_video` si la salida es < 1080p. Varias tomas por escena.
- [ ] **Step 5 (responsable):** aprobar una toma por escena. Registrar en `landing/media/README.md`
  por pieza: escena, prompt, modelo, semilla, fecha, id del trabajo de Higgsfield.
- [ ] **Step 6:** `build-sequences.sh <chapter> <video>`: con ffmpeg genera
  `desktop/` (`fps=24,scale=1920:-2`) y `mobile/` (versión 9:16 si existe, si no recorte centrado, `scale=1080:-2`)
  en WebP (`-c:v libwebp -quality 75`), `key.webp` del cuadro 1 y `manifest.json`
  (`id`, `fps`, `frameCount`, `width`, `height` por resolución). Falla si falta ffmpeg.
- [ ] **Step 7:** Ejecutar el script para las cuatro escenas y comprobar con `du -sh landing/public/media`
  que se cumple el presupuesto; si no, bajar `fps` o `quality` de la escena más pesada.
- [ ] **Step 8:** Commit `feat(landing): escenas generadas y secuencias de cuadros` (cuerpo: modelos y aprobación); integrar.

### Task 5: Motor de secuencias de cuadros

Rama: `feat/landing-secuencias`.

**Files:**
- Create: `landing/src/sequence/types.ts`, `landing/src/sequence/math.ts`, `landing/src/sequence/loader.ts`,
  `landing/src/sequence/FrameSequence.tsx`
- Test: `landing/src/sequence/math.test.ts`, `landing/src/sequence/FrameSequence.test.tsx`

**Interfaces:**
- Produces:
  - `type ChapterId = "apertura" | "problema" | "priorizar" | "reparado"`
  - `type Resolution = "desktop" | "mobile"`
  - `interface SequenceManifest { id: ChapterId; fps: number; frameCount: number; resolutions: Record<Resolution, { width: number; height: number }> }`
  - `frameIndexForProgress(progress: number, frameCount: number): number` (progreso fuera de 0–1 se recorta; 0 → 0, 1 → frameCount − 1)
  - `preloadOrder(frameCount: number, stride: number): number[]` (0, luego múltiplos de `stride`, luego el resto; sin repetidos)
  - `nearestLoaded(target: number, loaded: ReadonlySet<number>): number | null`
  - `pickResolution(viewportWidth: number, viewportHeight: number): Resolution` (`mobile` si alto > ancho o ancho < 768)
  - `coverRect(srcW: number, srcH: number, dstW: number, dstH: number): { sx: number; sy: number; sw: number; sh: number }` (recorte tipo `object-fit: cover`)
  - `createFrameLoader(baseUrl: string, manifest: SequenceManifest, resolution: Resolution): { start(): void; cancel(): void; get(index: number): ImageBitmap | HTMLImageElement | undefined; loaded: ReadonlySet<number> }`
  - `<FrameSequence chapter={ChapterId} progress={number} alt={string} />` — `<canvas>` con `role="img"` y `aria-label={alt}`.

- [ ] **Step 1: Pruebas que fallan** — `math.test.ts`:
  ```ts
  expect(frameIndexForProgress(0, 120)).toBe(0);
  expect(frameIndexForProgress(1, 120)).toBe(119);
  expect(frameIndexForProgress(0.5, 120)).toBe(60);
  expect(frameIndexForProgress(-0.2, 120)).toBe(0);
  expect(frameIndexForProgress(1.4, 120)).toBe(119);
  expect(preloadOrder(10, 4)).toEqual([0, 4, 8, 1, 2, 3, 5, 6, 7, 9]);
  expect(nearestLoaded(50, new Set([0, 40, 56]))).toBe(56);
  expect(nearestLoaded(5, new Set())).toBeNull();
  expect(pickResolution(1440, 900)).toBe("desktop");
  expect(pickResolution(390, 844)).toBe("mobile");
  expect(pickResolution(1024, 1366)).toBe("mobile");
  expect(coverRect(1920, 1080, 1080, 1080)).toEqual({ sx: 420, sy: 0, sw: 1080, sh: 1080 });
  ```
  Empate en `nearestLoaded`: gana el anterior (`nearestLoaded(50, new Set([45, 55]))` → 45).
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar `math.ts` (funciones puras) y `loader.ts` (descarga en el orden de
  `preloadOrder` con `stride` = `fps / 2`, máximo 6 peticiones simultáneas, `createImageBitmap`
  cuando exista).
- [ ] **Step 4:** `FrameSequence.tsx`: carga `manifest.json` del capítulo, elige resolución con
  `pickResolution` (y la recalcula en `resize`/`orientationchange`), dibuja con `coverRect` y
  `devicePixelRatio` (máx. 2) en `requestAnimationFrame` solo cuando cambia el índice, usa
  `nearestLoaded` si el cuadro pedido no está. Prueba: con un *mock* de `fetch` y del canvas, el
  componente expone `role="img"` con su `alt` y pide `manifest.json` del capítulo.
- [ ] **Step 5:** `npm test` → PASA. Commit `feat(landing): motor de secuencias de cuadros`; integrar.

### Task 6: Capítulos, *scroll* y textos

Rama: `feat/landing-capitulos`.

**Files:**
- Create: `landing/src/content/copy.ts`, `landing/src/scroll/useSmoothScroll.ts`,
  `landing/src/scroll/useChapterProgress.ts`, `landing/src/a11y/useReducedMotion.ts`,
  `landing/src/components/RevealText.tsx`, `landing/src/chapters/{Apertura,Problema,Priorizar,Reparado}.tsx`,
  `landing/src/components/SiteHeader.tsx`
- Modify: `landing/src/App.tsx`
- Test: `landing/src/a11y/useReducedMotion.test.ts`, `landing/src/chapters/chapters.test.tsx`

**Interfaces:**
- Consumes: `<FrameSequence>` y `ChapterId` (Tarea 5), `<Logo>` (Tarea 3).
- Produces: `useReducedMotion(): boolean` (escucha `matchMedia("(prefers-reduced-motion: reduce)")`);
  `useChapterProgress(ref: RefObject<HTMLElement>, opts: { pinLengthVh: number }): number` (0–1,
  con ScrollTrigger `pin` + `scrub`); `useSmoothScroll(enabled: boolean): void` (Lenis sincronizado
  con `gsap.ticker` y `ScrollTrigger.update`); `COPY` (objeto con todos los textos por capítulo).

- [ ] **Step 1:** Redactar `copy.ts` con los textos de la sección 6 del diseño (titular editorial
  breve + una línea de apoyo por capítulo; capítulo 3 con «U = 0,5·S + 0,3·F + 0,2·P» y el
  significado de S, F y P). Pasárselos al responsable para revisar antes de seguir.
- [ ] **Step 2: Pruebas que fallan** — `useReducedMotion` devuelve `true` con `matchMedia` simulado
  en `reduce` y cambia al emitir el evento `change`. `chapters.test.tsx`: con movimiento reducido,
  cada capítulo de secuencia renderiza `<img src=".../key.webp">` con su `alt` en lugar del canvas,
  y todos los titulares de `COPY` están en el documento.
- [ ] **Step 3:** `npm test` → FALLA.
- [ ] **Step 4:** Implementar los hooks, `RevealText` (líneas con máscara que entran según el
  progreso; sin animación con movimiento reducido) y los cuatro capítulos con `pinLengthVh` 250–400.
  Transiciones entre capítulos con desvanecido + desenfoque (*shadow vanishing*) en la última fracción
  del progreso. `SiteHeader`: logo + enlace «Descargar» a `#descarga`, fijo, discreto. Grano
  fílmico como capa fija de ruido SVG al 4–6 % de opacidad (oculta con movimiento reducido).
  `Apertura` revela el `<Logo variant="stacked">` sobre la secuencia.
- [ ] **Step 5:** `npm test` → PASA. Revisar en la vista previa de Vercel en escritorio y en el
  celular del responsable. Commit `feat(landing): capítulos guiados por el scroll`; integrar.

### Task 7: Teléfono 3D con capturas reales

Rama: `feat/landing-telefono-3d`.

**Files:**
- Create: `landing/public/media/app/{captura-foto,captura-severidad,captura-enviado,captura-mapa}.webp`,
  `landing/src/three/isWebGLAvailable.ts`, `landing/src/three/PhoneModel.tsx`,
  `landing/src/three/PhoneStage.tsx`, `landing/src/chapters/Reportar.tsx`
- Test: `landing/src/three/PhoneStage.test.tsx`

**Interfaces:**
- Consumes: `useChapterProgress`, `useReducedMotion` (Tarea 6).
- Produces: `isWebGLAvailable(): boolean`; `<PhoneStage progress={number} screens={readonly string[]} />`.

- [ ] **Step 1:** Tomar las capturas en el emulador de Android (o el celular) con el backend local
  y `seed-demo`. Las cuentas `@demo.invalid` no pueden iniciar sesión (fila 85): crear una cuenta
  temporal de prueba y borrarla al terminar (como en la fila 89). Pantallas: foto y ubicación, severidad,
  reporte enviado, mapa. Revisar una por una que no haya datos personales; exportar WebP 1080 px de ancho.
- [ ] **Step 2: Prueba que falla** — `PhoneStage.test.tsx`: con `isWebGLAvailable` simulado en
  `false` (o movimiento reducido), renderiza `<img>` de la primera captura con `alt` descriptivo y
  no monta el `<Canvas>`.
- [ ] **Step 3:** `npm test` → FALLA.
- [ ] **Step 4:** Implementar `PhoneModel` en código (caja redondeada `RoundedBox` de drei, marco
  `--ink`, pantalla como plano con la textura de la captura, reflejo sutil `Environment` local sin
  HDR remoto), rotación y entrada ligadas al progreso, cambio de captura por tramos de progreso.
  `PhoneStage` se carga con `React.lazy` y solo se monta cuando el capítulo está a ≤ 1 pantalla
  (IntersectionObserver); `dpr` máx. 1,5 en móvil.
- [ ] **Step 5:** `npm test` → PASA; verificar 60 fps en escritorio (Performance de Chrome DevTools)
  y fluidez en el celular. Commit `feat(landing): teléfono 3D con capturas reales`; integrar.

### Task 8: Capítulo del panel, descarga y pie

Rama: `feat/landing-descarga`.

**Files:**
- Create: `landing/public/media/panel/priorizacion.webp`, `landing/src/chapters/Panel.tsx`,
  `landing/src/config/release.ts`, `landing/src/components/DownloadSection.tsx`,
  `landing/src/components/SiteFooter.tsx`, `landing/src/components/SkipLink.tsx`
- Test: `landing/src/config/release.test.ts`, `landing/src/components/DownloadSection.test.tsx`,
  `landing/src/components/SkipLink.test.tsx`

**Interfaces:**
- Produces: `interface Release { version: string; apkUrl: string; sizeBytes: number; sha256: string; minAndroid: string }`;
  `export const RELEASE: Release | null = null`; `formatSize(bytes: number): string`;
  `<DownloadSection release={Release | null} />` con `id="descarga"` y `tabIndex={-1}`.

- [ ] **Step 1: Pruebas que fallan** —
  `formatSize(25_480_000)` → `"24,3 MB"`; `formatSize(900_000)` → `"0,9 MB"`.
  `DownloadSection` con `null`: muestra «Próximamente», no hay enlace `.apk`, y explica que la
  app está en pruebas. Con un `Release`: enlace «Descargar Street Repo para Android» a `apkUrl`,
  versión, tamaño con coma, «Android {minAndroid} o superior», SHA-256 en `<code>`, un QR (SVG
  generado con `qrcode` hacia `apkUrl`, con `alt`) y los pasos de instalación (permitir
  instalar apps desconocidas, abrir el archivo, instalar).
  `SkipLink`: primer elemento enfocable, texto «Saltar a la descarga», `href="#descarga"`.
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar. `Panel.tsx`: la captura real de Priorización (de
  `docs/capturas/objetivo-3/` si la calidad alcanza; si no, nueva con `seed-demo`) en perspectiva
  con CSS 3D y paralaje, con la atribución «© colaboradores de OpenStreetMap» visible sobre el mapa.
  `SiteFooter`: logo, «Proyecto de grado · Ingeniería de Software · Universidad Cooperativa de
  Colombia, campus Pasto», «Imágenes y videos ilustrativos generados con IA», año.
  `App.tsx` compone en el orden del guion: `SkipLink`, `SiteHeader`, Apertura, Problema, Reportar,
  Priorizar, Panel, Reparado, `DownloadSection`, `SiteFooter`.
- [ ] **Step 4:** `npm test` → PASA. Commit `feat(landing): panel, descarga y pie`; integrar.

### Task 9: Rendimiento, accesibilidad y cierre

Rama: `chore/landing-cierre`.

**Files:**
- Create: `landing/scripts/check-media-budget.mjs`
- Test: `landing/scripts/check-media-budget.test.ts`
- Modify: `.github/workflows/ci.yml` (paso de presupuesto), `landing/README.md`, `README.md`
  (sección «Página de presentación»), `AGENTS.md` (Vercel en la tabla 3 y `landing/` en la 4.3),
  `docs/ajustes-tesis.md`, `CHANGELOG.md` («Sin publicar»), `docs/bitacora.md`

**Interfaces:**
- Produces: `checkBudget(sizes: { initialBytes: number; desktopBytes: number; mobileBytes: number }): string[]`
  (lista de incumplimientos; vacía si cumple) y un CLI que mide `landing/public/media` y sale con 1 si hay incumplimientos.

- [ ] **Step 1: Prueba que falla** — `checkBudget({ initialBytes: 6e6, desktopBytes: 45e6, mobileBytes: 25e6 })` → `[]`;
  con `desktopBytes: 46e6` → un mensaje que nombra «escritorio» y «45 MB».
  «Inicial» = `apertura/` de la resolución + fuentes + `favicon`.
- [ ] **Step 2:** `npm test` → FALLA; implementar; `npm test` → PASA; añadir `node scripts/check-media-budget.mjs` a la CI.
- [ ] **Step 3:** Lighthouse (Chrome DevTools MCP) sobre la vista previa: accesibilidad y buenas
  prácticas ≥ 90, LCP < 2,5 s con 4G simulado. Recorrido completo solo con teclado. Prueba en el
  celular del responsable. Corregir lo que falle en esta misma rama.
- [ ] **Step 4:** Documentación: README de `landing/` (arrancar, generar secuencias, presupuesto,
  despliegue), README raíz, `AGENTS.md`, fila en `docs/ajustes-tesis.md` («Página de presentación
  y descarga; sin HU en la tesis», sección a definir con el asesor), `CHANGELOG.md`, bitácora (cierre
  de la fila 99) y Linear.
- [ ] **Step 5:** Commit `chore(landing): presupuesto de medios, auditoría y documentación`;
  integrar a `main`; verificar CI y el despliegue de producción en Vercel; borrar la rama.
