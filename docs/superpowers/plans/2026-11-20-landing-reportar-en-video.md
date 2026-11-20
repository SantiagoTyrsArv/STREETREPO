# Reportar en video (entrega 2) — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la pantalla del teléfono 3D de Reportar muestre un video real de la app avanzando con el *scroll*, que al final salga un abanico de 3 teléfonos con el multirreporte y que el texto entre con *slide in words*.

**Architecture:** El flujo real se graba en el emulador (stack aparte con datos de demostración) y se convierte en una secuencia de cuadros WebP de la pantalla; el teléfono la pinta en una `CanvasTexture` según el progreso, reutilizando el cargador de secuencias existente. Dos teléfonos más, con capturas reales fijas, se abren en abanico en el último tramo.

**Tech Stack:** Emulador Android (AVD `streetrepo_pixel7`), `adb screenrecord`, `ffmpeg-static`, React 18, R3F/three, vitest.

**Spec:** `docs/superpowers/specs/2026-11-20-landing-textos-reportar-video-design.md` (sección 6.10)

## Global Constraints

- Rama `feat/landing-reportar-video` desde `main`; sin PR; *merge* `--no-ff`.
- Datos: solo el stack aparte `street-repo-e2e` (base nueva, OSM y `seed-demo`), cuentas temporales `@example.com` que se suprimen al terminar (`POST /api/v1/me/data-deletion-requests` → 201). Nunca la base de desarrollo (tiene cuentas reales).
- La foto del daño es una imagen de demostración (`demo-*.jpg` con su franja «DEMO · imagen generada»), como en la tarea 7 (fila 106).
- Sin generación con IA (si hiciera falta, un `.md` para claude.ai).
- Presupuesto: la secuencia de la pantalla suma como mucho 6 MB.
- Movimiento reducido: las capturas fijas de hoy, sin abanico.
- Los originales (videos, capturas sin recortar) van en `landing/media/originals/app/` (fuera de git).
- Antes de cada *commit*: `cd landing && npm test && npm run lint && npm run typecheck && npm run format:check`.

## Review Focus

1. Volver hacia atrás con el *scroll* retrocede el video de la pantalla al cuadro correcto (sin quedarse en el último).
2. Con red lenta, la pantalla muestra el cuadro cargado más cercano o la captura fija, nunca negro.
3. El abanico no tapa el texto en el celular (390 × 844) ni se sale de la pantalla en escritorio.
4. El lector de pantalla recibe una descripción de lo que muestra cada tramo (una vez, no en cada cuadro).
5. Los teléfonos no dibujan fuera de pantalla ni en reposo (lienzo a demanda, como hoy).

---

### Task 1: Grabación del flujo real en el emulador

**Files:**
- Create: `landing/media/originals/app/reporte.mp4`, `landing/media/originals/app/duplicado.png`, `landing/media/originals/app/confirmar.png` (fuera de git)
- Modify: `landing/media/README.md` (procedimiento y datos de la grabación)

- [ ] **Step 1:** Levantar el stack aparte (`docker compose -p street-repo-e2e -f infra/docker-compose.yml --env-file .env up -d --build --wait db api` con las variables de `infra/scripts/e2e-panel.sh`), `osm-import` si la tabla `via` está vacía y `seed-demo`. Comprobar `GET http://localhost:8001/health` → 200.
- [ ] **Step 2:** Compilar e instalar la app contra `http://10.0.2.2:8001` en el AVD `streetrepo_pixel7`; poner `demo-01-hueco.jpg` como póster de la escena virtual de la cámara (como en la fila 106). Crear la cuenta temporal A desde la app.
- [ ] **Step 3:** Grabar con `adb shell screenrecord --bit-rate 8000000` el flujo continuo de A: Mapa → Reportar → foto → ubicación → Continuar → severidad alta → Enviar → reporte enviado (≈ 15–25 s, sin pausas largas). Descargar a `originals/app/reporte.mp4`.
- [ ] **Step 4:** Cuenta temporal B: intentar reportar en el mismo punto → captura de «Posible duplicado» (`duplicado.png`); en el mapa, abrir la ficha del reporte de A → captura con «Confirmar este daño» (`confirmar.png`).
- [ ] **Step 5:** Suprimir A y B (`POST /me/data-deletion-requests` → 201; su inicio de sesión → 401) y detener el stack. Registrar en `media/README.md`: fecha, flujo, cuentas suprimidas, recorte de la barra de estado (136 px).
- [ ] **Step 6:** Commit `docs(landing): grabación del flujo real para Reportar`.

### Task 2: Secuencia de la pantalla y capturas del abanico

**Files:**
- Create: `landing/scripts/build-screen-sequence.ts`, `landing/scripts/build-screen-sequence.test.ts`
- Create: `landing/public/media/app/reporte/frame_NNNN.webp`, `landing/public/media/app/reporte/manifest.json`, `landing/public/media/app/captura-duplicado.webp`, `landing/public/media/app/captura-confirmar.webp`

**Interfaces:**
- Consumes: `parseDimensions`, `ffmpegArgs` (exportadas de `scripts/build-sequences.ts`).
- Produces: `manifest.json` con la forma `SequenceManifest` (`id: "reporte"`, ambas resoluciones iguales); `screenFilter(fps: number, width: number, cropTop: number): string` → `fps={fps},crop=iw:ih-{cropTop}:0:{cropTop},scale={width}:-2:flags=lanczos`.

- [ ] **Step 1: Pruebas que fallan:** `screenFilter(10, 540, 136)` = `"fps=10,crop=iw:ih-136:0:136,scale=540:-2:flags=lanczos"`; `parseScreenArgs(["in.mp4"])` → `{ video: "in.mp4", fps: 10, width: 540, quality: 70, cropTop: 136 }`; rechaza `--fps 0`.
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar (mismo patrón que `build-sequences.ts`). Generar la secuencia y las dos capturas (recortadas igual, WebP 1080 de ancho, calidad 80). Comprobar con `du -sh` ≤ 6 MB; si no, bajar `--fps` a 8 o `--quality` a 60.
- [ ] **Step 4:** `npm test` → PASA. Commit `feat(landing): secuencia de la pantalla de la app y capturas del abanico`.

### Task 3: Pantalla del teléfono que avanza con el *scroll*

**Files:**
- Create: `landing/src/three/screenFrames.ts`, `landing/src/three/useScreenSequence.ts`
- Modify: `landing/src/three/PhoneModel.tsx`, `PhoneCanvas.tsx`, `PhoneStage.tsx`, `landing/src/chapters/Reportar.tsx` (`PIN_LENGTH_VH` 400 → 520), `landing/src/content/copy.ts`
- Test: `landing/src/three/screenFrames.test.ts`, `landing/src/three/PhoneStage.test.tsx`

**Interfaces:**
- Consumes: `createFrameLoader`, `frameIndexForProgress`, `nearestLoaded` (`src/sequence/`).
- Produces:
  - `VIDEO_FROM = 0.1`, `VIDEO_TO = 0.62`; `screenProgress(progress: number): number` (0 antes de `VIDEO_FROM`, 1 después de `VIDEO_TO`, lineal entre medio).
  - `captionForProgress(progress: number): string` — descripción accesible del tramo (foto y ubicación · severidad · enviado · varios ciudadanos), del `copy.reportar.captions`.
  - `useScreenSequence(enabled: boolean): { canvas: HTMLCanvasElement | null; draw(progress: number): boolean }` — carga `public/media/app/reporte/` y dibuja en un lienzo el cuadro del progreso o el cargado más cercano; devuelve `true` si cambió.

- [ ] **Step 1: Pruebas que fallan:** `screenProgress(0)` = 0; `screenProgress(0.62)` = 1; `screenProgress(0.36)` ≈ 0,5; `screenProgress(1)` = 1; al retroceder de 0,6 a 0,2 el índice de `frameIndexForProgress(screenProgress(p), 200)` baja (Review Focus 1). `captionForProgress` devuelve 4 textos distintos en 0,15, 0,35, 0,55, 0,8. `PhoneStage.test`: con movimiento reducido sigue mostrando la captura fija; el texto `aria-live` cambia solo al cambiar de tramo (Review Focus 4).
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar. La textura de la pantalla es una `CanvasTexture` sobre el lienzo de `useScreenSequence`; en cada cambio de progreso se dibuja, se marca `needsUpdate` y se invalida el lienzo R3F (sigue `frameloop="demand"`). Mientras no haya cuadros cargados se usa la textura de la captura fija (Review Focus 2).
- [ ] **Step 4:** `npm test` → PASA. Commit `feat(landing): la pantalla del teléfono muestra la app en uso con el scroll`.

### Task 4: Abanico de 3 teléfonos y *slide in words*

**Files:**
- Create: `landing/src/three/fan.ts`
- Modify: `landing/src/three/PhoneModel.tsx` (componente de teléfono reutilizable), `PhoneCanvas.tsx`, `landing/src/components/RevealText.tsx` (`motion?: "rise" | "slide"`), `RevealText.css`, `landing/src/chapters/Reportar.tsx`, `Reportar.css`
- Test: `landing/src/three/fan.test.ts`, `landing/src/components/RevealText.test.tsx`

**Interfaces:**
- Produces:
  - `FAN_FROM = 0.66`, `FAN_TO = 0.86`; `fanSpread(progress: number): number` (0 → 1 con *ease-out*).
  - `fanPose(spread: number, side: -1 | 1): { x: number; z: number; rotZ: number; rotY: number; scale: number }` — en 1: `x = side · 0.95`, `z = −0.35`, `rotZ = −side · 0.31` (≈ 18°), `rotY = side · 0.25`, `scale = 0.92`; en 0 todo en el teléfono central (`x = 0`, `z = −0.05`, `scale = 0.9`).
  - `RevealText` con `motion="slide"`: cada palabra entra desde la derecha (`translateX(0.6em)` → 0) con opacidad 0 → 1, en cascada.

- [ ] **Step 1: Pruebas que fallan:** `fanSpread(0.5)` = 0; `fanSpread(0.86)` = 1; `fanSpread(1)` = 1; creciente. `fanPose(1, 1).rotZ` ≈ −0,31; `fanPose(1, -1).x` = −0,95; `fanPose(0, 1).x` = 0. `RevealText` con `split="words" motion="slide"` y progreso en `from`: la primera palabra tiene `translateX(` positivo y `opacity` 0; en `to`, `translateX(0` y `opacity` 1.
- [ ] **Step 2:** `npm test` → FALLA.
- [ ] **Step 3:** Implementar. Los dos teléfonos laterales usan `captura-duplicado.webp` (izquierda) y `captura-confirmar.webp` (derecha), detrás del central; en el celular el lienzo conserva su tamaño y el abanico cabe (escala del grupo según la proporción del lienzo) (Review Focus 3). El texto de Reportar (título y *lead*) usa `split="words" motion="slide"`.
- [ ] **Step 4:** `npm test` → PASA. Revisar a ojo en 1280 px y 390 px. Commit `feat(landing): abanico de teléfonos y texto que entra deslizándose`.

### Task 5: Verificación, registro e integración

- [ ] **Step 1:** `npm test && npm run lint && npm run typecheck && npm run format:check && npm run build` → verde.
- [ ] **Step 2:** Vista previa en escritorio y celular emulado: Review Focus 1–5 a mano (retroceder, red lenta con DevTools «Slow 4G», abanico en 390 px, árbol de accesibilidad, sin cuadros fuera de pantalla).
- [ ] **Step 3:** Fluidez con CPU ×4 en celular (3 pasadas, mediana de cuadros > 50 ms en Reportar = la de `main`); peso de `public/media/app/reporte` ≤ 6 MB.
- [ ] **Step 4:** Bitácora (fila nueva), CHANGELOG, AGENTS.md, Linear. Revisión final de la rama; correcciones con prueba que falle primero; CI en verde; *merge* `--no-ff`; borrar la rama.
