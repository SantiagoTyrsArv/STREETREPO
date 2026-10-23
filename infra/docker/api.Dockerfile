# Imagen de la API: multi-etapa, sin herramientas de compilación ni secretos, usuario no root.
FROM ghcr.io/astral-sh/uv:0.13.5 AS uv

FROM python:3.13-slim AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.13-slim AS runtime
ENV PATH="/srv/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --system app && useradd --system --gid app --no-create-home app
WORKDIR /srv
COPY --from=build /srv/.venv /srv/.venv
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
# Carpeta del volumen de fotos: Docker copia su dueño al volumen nuevo, así el usuario
# sin privilegios puede escribir en ella.
RUN mkdir -p /srv/storage/photos && chown app:app /srv/storage/photos
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
# Un solo proceso: los contadores del límite de intentos viven en memoria (decisión 25).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--workers", "1"]
