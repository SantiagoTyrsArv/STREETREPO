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
```

## Identidad

Los colores y la tipografía viven solo en `src/styles/tokens.css`. `src/lib/contrast.test.ts`
comprueba que cada combinación de texto cumpla WCAG AA (contraste ≥ 4,5:1).
