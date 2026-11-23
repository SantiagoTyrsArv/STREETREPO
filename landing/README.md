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

## Identidad

Los colores y la tipografía viven solo en `src/styles/tokens.css`. `src/lib/contrast.test.ts`
comprueba que cada combinación de texto cumpla WCAG AA (contraste ≥ 4,5:1).

## Despliegue

Vercel publica `landing/` en https://streetrepo.vercel.app/ (raíz del proyecto `landing`,
framework Vite, salida `dist`). Crea una vista previa por cada rama subida. `vercel.json` añade
las cabeceras de seguridad (CSP sin orígenes externos, HSTS, `nosniff`, `Referrer-Policy` y
`Permissions-Policy`) y guarda en caché por un año `/assets/` (nombres con hash) y `/media/`.
