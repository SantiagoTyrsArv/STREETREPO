# Diagrama de despliegue UML

Fuente canónica desde el 2026-11-23. Es la versión en Mermaid del diagrama de despliegue de Lucid
(«Street Repo - Diagrama de Despliegue UML», última edición del 2026-10-15), con su mismo contenido.
Las diferencias con el despliegue actual están en la sección final.

```mermaid
flowchart LR
    subgraph telefono["«device» Smartphone del Ciudadano (Android / iOS)"]
        apk["«artifact»<br/>street-repo (APK / IPA)<br/><i>App Flutter: cámara y GPS</i>"]
    end

    subgraph pc["«device» PC del Administrador"]
        nav["«artifact»<br/>Navegador web<br/><i>carga la SPA React + Leaflet</i>"]
    end

    subgraph servidor["«execution environment» Servidor Linux con Docker Compose"]
        api["«container» api<br/>«artifact» FastAPI + Uvicorn<br/><i>REST, JWT, motor de priorización</i><br/>puerto 8000"]
        panelweb["«container» panel-web<br/>«artifact» build estático React<br/>puerto 80"]
        db[("«container» db<br/>PostgreSQL + PostGIS<br/>puerto 5432")]
        vol[("«volume» evidencias<br/><i>fotos de los reportes,<br/>montado en el contenedor api</i>")]
    end

    subgraph osm["«cloud» Servicios externos OpenStreetMap"]
        nominatim["«web service» Nominatim<br/><i>geocodificación inversa</i>"]
        overpass["«web service» Overpass API<br/><i>hospitales y colegios</i>"]
    end

    apk -- "HTTPS REST + JWT" --> api
    nav -- "HTTPS" --> panelweb
    nav -- "HTTPS REST + JWT" --> api
    api -- "TCP 5432" --> db
    api -- "E/S de archivos" --> vol
    api -- "HTTPS" --> nominatim
    api -- "HTTPS" --> overpass
```

## Diferencias conocidas con el despliegue actual (pendientes de decisión)

- Delante de la API y del panel hay un proxy HTTPS con Caddy (HU-17, fila 121 de la bitácora); el
  despliegue en servidor está pospuesto y la app se prueba contra el backend local (fila 123).
- En `infra/docker-compose.yml` el panel es el servicio `admin-web` (nginx sin root), el volumen de
  fotos se llama `photos` y un servicio `migrate` aplica las migraciones antes de la API.
- La API no llama a Nominatim ni a Overpass por cada solicitud: `osm-import` carga los datos de OSM
  a PostGIS (sección 3.1 de `AGENTS.md`).
- La página de presentación (`landing/`) se despliega en Vercel, fuera del servidor (decisión 99).
