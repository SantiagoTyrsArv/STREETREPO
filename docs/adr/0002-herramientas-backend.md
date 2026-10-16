# 0002 · Herramientas del backend

- **Fecha:** 2026-10-15
- **Tipo:** decisión menor (no cambia el stack fijo)
- **Estado:** aceptada

## Contexto

El stack fija FastAPI y PostgreSQL + PostGIS, pero deja abiertas las herramientas de acceso a datos,
dependencias y versión de Python.

## Decisión

| Necesidad | Elección | Motivo |
|---|---|---|
| ORM | **SQLAlchemy 2.x** (estilo tipado, síncrono) | Estándar de facto, compatible con Alembic y `mypy`; el modo síncrono basta para el MVP y simplifica las pruebas |
| Tipos espaciales | **GeoAlchemy2** | Integra `geometry`/`geography` y funciones `ST_*` con SQLAlchemy |
| Controlador | **psycopg 3** | Controlador actual de PostgreSQL, consultas parametrizadas en el servidor |
| Migraciones | **Alembic** | Indicado en la guía |
| Configuración | **pydantic-settings** | Variables de entorno tipadas y validadas |
| Dependencias | **uv** + `uv.lock` | Versiones fijadas y reproducibles; instalación rápida en CI y Docker |
| Python | **3.13** | Versión estable con soporte amplio de librerías con extensiones nativas |
| Calidad | ruff, mypy `--strict`, pytest, pytest-cov, pip-audit | Indicado en la guía (8.2) |

## Consecuencias

- Los endpoints con acceso a base de datos se declaran `def` (FastAPI los ejecuta en un *pool* de hilos).
- Si más adelante se necesita I/O asíncrono intensivo, migrar a `AsyncSession` es local a `app/core/database.py`.
