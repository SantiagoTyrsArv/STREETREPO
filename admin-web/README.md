# Panel administrativo

Panel web de la Secretaría de Infraestructura: React 18 + TypeScript `strict` + Vite, con Leaflet
para los mapas. Se construye en la fase 6 (plan en
`docs/superpowers/plans/2026-11-08-panel-administrativo-objetivo-3.md`).

## Requisitos

- Node.js 22.12 o superior (la CI usa Node 22 LTS).
- La API en marcha (ver el README de la raíz) con el origen del panel en `CORS_ORIGINS`
  (`http://localhost:5173` en desarrollo).

## Desarrollo

```bash
cp .env.example .env.local   # VITE_API_BASE_URL y, si quieres, VITE_TILE_URL
npm ci
npm run dev                  # http://localhost:5173
```

## Comandos

| Comando                | Qué hace                                                            |
| ---------------------- | ------------------------------------------------------------------- |
| `npm run lint`         | ESLint (TypeScript, hooks de React y accesibilidad)                 |
| `npm run format:check` | Prettier, sin modificar archivos (`npm run format` los corrige)     |
| `npm run typecheck`    | `tsc --noEmit` en modo `strict`                                     |
| `npm test`             | Pruebas con Vitest y Testing Library                                |
| `npm run build`        | Compila a `dist/`                                                   |
| `npm run gen:api`      | Regenera `src/api/schema.d.ts` desde el OpenAPI de la API en marcha |

Para regenerar los tipos sin levantar la API, exporta el contrato desde `backend/` y pásalo como
archivo:

```bash
cd ../backend
APP_ENV=test uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../admin-web/openapi.json
cd ../admin-web
npx openapi-typescript openapi.json -o src/api/schema.d.ts && rm openapi.json
```

## Convenciones

- **Tokens visuales** en `src/theme/tokens.css` (guía 10.1 y Figma). Ningún color ni tipografía va
  suelto en un componente. Las fuentes Archivo y Manrope se empaquetan con `@fontsource` (sin CDN).
- **Formatos** en `src/format/format.ts`: coma decimal (`8,70`) y fechas en hora de Bogotá
  («13 oct»).
- **El panel no calcula reglas del dominio** (U, transiciones, orden del ranking): muestra lo que
  responde la API.
- **Sesión** (decisión 42): el token de acceso vive en memoria y el de refresco en una cookie
  `HttpOnly`; ESLint prohíbe `localStorage` y `sessionStorage`.
- Versiones exactas en `package.json` (`save-exact=true` en `.npmrc`).
