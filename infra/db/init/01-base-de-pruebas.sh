#!/bin/sh
# Crea la base de pruebas junto a la de desarrollo (solo en el primer arranque del volumen).
# Las pruebas de integración solo corren contra una base cuyo nombre termina en _test.
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "CREATE DATABASE \"${POSTGRES_DB}_test\" OWNER \"$POSTGRES_USER\";"
