# Imagen del panel: se compila con Node y lo sirve nginx sin root, solo archivos estáticos.
# Contexto: la raíz del repositorio (ver admin-web.Dockerfile.dockerignore).
FROM node:22.23.0-alpine AS build
WORKDIR /srv
COPY admin-web/package.json admin-web/package-lock.json admin-web/.npmrc ./
RUN npm ci
COPY admin-web/ ./
# Vite deja estos valores dentro del JavaScript: no son secretos, son direcciones públicas.
ARG VITE_API_BASE_URL
ARG VITE_TILE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} VITE_TILE_URL=${VITE_TILE_URL}
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.31.7-alpine AS runtime
# La imagen sustituye ${API_ORIGIN} y ${TILE_ORIGIN} de la plantilla al arrancar.
ENV API_ORIGIN=http://localhost:8000 TILE_ORIGIN=https://tile.openstreetmap.org
COPY infra/docker/admin-web.nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /srv/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
