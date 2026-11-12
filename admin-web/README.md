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
| `npm run e2e`          | Pruebas de punta a punta con Playwright (ver abajo)                 |

Para regenerar los tipos sin levantar la API, exporta el contrato desde `backend/` y pásalo como
archivo:

```bash
cd ../backend
APP_ENV=test uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > ../admin-web/openapi.json
cd ../admin-web
npx openapi-typescript openapi.json -o src/api/schema.d.ts && rm openapi.json
```

## Servir el panel con Docker

`docker compose -f infra/docker-compose.yml --env-file .env up --build` (desde la raíz) compila el
panel y lo sirve con nginx en `http://localhost:8080`. La imagen (`infra/docker/admin-web.Dockerfile`)
corre sin root y añade las cabeceras de seguridad (`infra/docker/admin-web.nginx.conf`): CSP que solo
permite la API y el proveedor de teselas, `X-Content-Type-Options`, `Referrer-Policy: no-referrer` y
`X-Robots-Tag`. Las teselas del mapa sí envían el origen como `Referer` (lo exige la política de uso
de OpenStreetMap), nunca la ruta.

## Pruebas de punta a punta

`e2e/panel.spec.ts` recorre los tres flujos críticos contra la API y la base reales. Lo normal es
lanzarlas con `infra/scripts/e2e-panel.sh` (desde la raíz), que prepara un stack aparte con datos de
demostración y una cuenta de un solo uso; los detalles están en el README de la raíz. Para
correrlas contra otro panel ya levantado:

```bash
E2E_BASE_URL=http://localhost:8080 E2E_ADMIN_EMAIL=… E2E_ADMIN_PASSWORD=… npm run e2e
```

Ojo: cambian el estado de un reporte y guardan pesos (una versión nueva que no se borra).

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
