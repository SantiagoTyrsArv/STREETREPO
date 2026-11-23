# Street Repo — página de presentación y descarga

Página estática que presenta Street Repo con un recorrido guiado por el _scroll_ y, más adelante,
aloja la descarga del APK. Diseño: `docs/superpowers/specs/2026-11-19-landing-descarga-apk-design.md`;
plan: `docs/superpowers/plans/2026-11-19-landing-descarga-apk.md`; bitácora, fila 99.

## Requisitos

- Node 22.12 o superior.

## Comandos

```bash
npm ci               # dependencias con el lock exacto
npm run dev          # servidor de desarrollo
npm test             # pruebas unitarias (vitest)
npm run lint         # eslint
npm run format:check # prettier
npm run typecheck    # tsc --noEmit
npm run build        # compilación estática en dist/
node scripts/check-media-budget.ts  # presupuesto de peso (después de build; también en la CI)
```

Presupuesto de peso (diseño, sección 7): carga inicial ≤ 6 MB (portada, fuentes e ícono), ≤ 45 MB
en escritorio y ≤ 25 MB en móvil. El 2026-11-23 medía 5,4 MB, 18,7 MB y 22,5 MB.

## Recorrido

Cada capítulo ocupa una pantalla. Al llegar a uno (ocupa ~40 % de la ventana, en cualquier
dirección), `useChapterPlayback` reproduce su animación en el tiempo, una sola vez por carga; si
se vuelve, queda en su estado final. Los cuadros de cada escena se descargan solo cuando el
capítulo está cerca, y la reproducción espera como máximo 2,5 s a que estén: con red lenta se ve
el cuadro clave o el más cercano cargado. Entre capítulos actúa un imán de proximidad
(`lenis/snap`). Con «reducir movimiento» no hay Lenis, imán ni reproducción: todo se muestra en su
estado final. Diseño: `docs/superpowers/specs/2026-11-23-landing-escenas-por-pantalla-design.md`.

## Prerenderizado

`npm run build` compila la página (`dist/`), luego `src/entry-server.tsx` con `vite build --ssr`
(en `dist-ssr/`, ignorada por git, sin copiar `public/`) y por último `scripts/prerender.ts`
inyecta ese HTML en el `<div id="root">` de `dist/index.html`. En el navegador, `main.tsx`
hidrata ese HTML (`hydrateRoot`); en `npm run dev` el contenedor llega vacío y monta desde cero.

Para que el HTML del servidor y el primer render del cliente coincidan, nada se decide durante el
render leyendo `window` o `document`: lo que solo se sabe en el navegador (WebGL, canvas,
orientación) se lee después de montar (`src/lib/useClientCheck.ts` o un efecto). Sin JavaScript,
un `<noscript><style>` en `index.html` deja el texto en su estado final y quita la máscara de la
portada.

Medido en producción el 2026-11-23 (412×915 móvil, 4G lento, CPU ×4, sin caché): LCP 2,2 s
(antes 3,1 s), CLS 0; Lighthouse móvil 100 en accesibilidad, buenas prácticas y SEO.

## Identidad

Los colores y la tipografía viven solo en `src/styles/tokens.css`. `src/lib/contrast.test.ts`
comprueba que cada combinación de texto cumpla WCAG AA (contraste ≥ 4,5:1).

## Despliegue

Vercel publica `landing/` en https://streetrepo.vercel.app/ (raíz del proyecto `landing`,
framework Vite, salida `dist`). Crea una vista previa por cada rama subida. `vercel.json` añade
las cabeceras de seguridad (CSP sin orígenes externos, HSTS, `nosniff`, `Referrer-Policy` y
`Permissions-Policy`) y guarda en caché por un año `/assets/` (nombres con hash) y `/media/`.
