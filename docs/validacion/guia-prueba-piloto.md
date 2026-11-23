# Guía de la prueba piloto (objetivo 4, HU-09)

Pasos para ejecutar la prueba piloto de la tesis (secciones 3.4 a 3.8 y 4.4) con el sistema. Las
herramientas ya existen (ADR 0008 y README, «Validación con el panel de referencia»). Esta guía
dice en qué orden usarlas y qué decisiones hay que tomar antes.

> Nada de lo que se calcule con datos de demostración o de prueba es un resultado de la tesis.
> Antes de la prueba real, borrar los datos de demostración (`seed-demo --remove`).

## 0. Decisiones previas del responsable

| # | Decisión | Por qué hace falta | Dónde queda |
|---|---|---|---|
| D1 | Servidor y dominio para la API y el panel | Los celulares de otras personas necesitan la API pública con HTTPS (HU-17) | `.env` del servidor |
| D2 | Quiénes reportan y cómo reciben la app | Define cuántas cuentas, la distribución del APK y los límites de uso | Bitácora |
| D3 | Las 2 o 3 zonas y su concentración (`alta`/`baja`) | Tesis 3.6; sin zonas no hay ronda | `docs/validacion/zonas.geojson` |
| D4 | Criterio para llamar «alta» o «baja» a una zona | La tesis 3.6 lo menciona, pero no fija un umbral (ver §2) | Tesis 3.6 y bitácora |
| D5 | Las 2 o 3 personas del panel de referencia | Tesis 3.7. No sirven como evaluadores a ciegas ni el autor del modelo ni una IA (fila 115) | Fuera del repositorio |
| D6 | Fechas: recolección, ronda y cierre | ARE-41 vence el 2026-12-11 | Linear |
| D7 | Juicio de expertos sobre criterios y pesos antes de la prueba | Tesis 3.7.1: se hace «antes de iniciar la prueba piloto» | Matriz de la sección 3.8 |

## 1. Desplegar (HU-17)

1. En el servidor: `docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml
   --env-file .env up -d --build` (README, «Despliegue con HTTPS»).
2. `curl https://<API_DOMAIN>/ready` responde 200.
3. Cargar OSM una vez: `… exec api python -m app.cli osm-import`.
4. Crear el administrador: `… exec api python -m app.cli create-admin --name … --email …`.
5. Compilar el APK de *release* con `--dart-define=API_BASE_URL=https://<API_DOMAIN>`. La
   configuración de *release* exige HTTPS.
6. Prueba de humo con dos cuentas: registro, reporte, «Posible duplicado», confirmación, y en el
   panel, el ranking y el detalle.
7. Respaldo inicial (README, «Respaldos»). Repetirlo cada día de recolección.

## 2. Definir las zonas

1. Elegir 2 o 3 sectores de Pasto que no se solapen, de tamaño parecido y caminables.
2. Asignar `alta` o `baja` con el criterio D4. **Propuesta (pendiente de aprobar):** marcar la
   concentración **antes** de recolectar, según la densidad esperada de reportes (vías principales y
   servicios críticos frente a barrios residenciales). Después de recolectar, comprobar que los
   reportes por km² de la zona `alta` superan a los de la `baja`. Si no es así, decirlo en la tesis.
   El sistema guarda la etiqueta, no la calcula.
3. Dibujar los polígonos (p. ej. en geojson.io) y guardarlos en `docs/validacion/zonas.geojson`, con
   el formato de [README](README.md).
4. Cargar: `… exec api python -m app.cli zones-import /ruta/zonas.geojson`. El archivo se copia
   al contenedor o se monta. Comprobar en el panel, Comparación › Zonas.

## 3. Recolectar los reportes

- Meta mínima: **5 reportes activos por zona**, el mínimo del sistema. El tamaño de la muestra
  (`sample_size`) se fija al abrir la ronda, según lo recolectado (tesis 3.6).
- Los reportantes usan la app normal: foto, ubicación y severidad. Cuando aparece «Posible
  duplicado», deciden en ese momento: el sistema registra el aviso y su decisión para medir la
  deduplicación.
- Los reportes deben ser de daños reales. No reportar el mismo daño a propósito para «probar» la
  deduplicación, porque eso contamina la medida.
- Ver el avance en el panel (Comparación › Zonas: reportes activos por zona).
- Límites: 10 reportes por hora por usuario y 100 por IP (`.env`). Si un grupo reporta desde la
  misma red Wi-Fi, revisar `REPORTS_PER_IP_PER_HOUR`.

## 4. Panel de referencia y ronda

1. Crear una cuenta por referente: `… exec api python -m app.cli create-evaluator --name …
   --email …`. Cada referente pone su contraseña por su cuenta o la recibe por un canal privado.
2. Abrir la ronda en el panel (Comparación › Rondas) con un nombre y `sample_size`. La ronda congela
   los reportes, su U y el orden del motor. Desde ese momento, los cambios de pesos o de estado no la
   afectan.
3. Indicar a los referentes, con el mismo texto para todos, que entren al panel y ordenen cada zona
   de más a menos urgente, sin hablar entre ellos. Enviar es definitivo.
4. No mirar ni comentar resultados mientras la ronda esté abierta: el panel no los muestra.
5. Cuando todos hayan enviado, cerrar la ronda.

## 5. Resultados y revisión de duplicados

1. Descargar `ficha.csv`, `resumen.csv`, `reportes.csv` y `avisos.csv` (Comparación ›
   Resultados).
2. Revisión manual de duplicados: en `avisos.csv` y `reportes.csv`, marcar si cada aviso era de
   verdad el mismo daño (tesis 4.4).
3. Guardar los CSV con la fecha, fuera de git si tienen datos personales. Los CSV usan «Evaluador k»
   y no traen nombres ni correos.
4. Llevar las cifras al capítulo 4: rho, tau, W, coincidencia ±1 y la prueba entre zonas. La
   interpretación de las hipótesis la hace el autor.
5. Registrar en la bitácora: fechas, número de reportantes, reportes por zona, `sample_size`,
   número de evaluadores y cualquier desviación.

## 6. Después

- Respaldo final de la base y de las fotos.
- Supresión: las solicitudes de los participantes se atienden como siempre (Ley 1581).
