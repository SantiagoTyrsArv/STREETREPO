# Diagrama de despliegue UML

Fuente canónica del despliegue. Refleja `infra/docker-compose.yml` más
`infra/docker-compose.prod.yml` (HTTPS con Caddy, HU-17) y la página en Vercel, al 2026-11-23
(fila 130 de la bitácora). El despliegue en servidor está pospuesto (fila 123): hoy la app se prueba
en el celular contra el mismo Compose levantado en el computador del responsable.

```mermaid
flowchart LR
    subgraph telefono["«device» Celular del ciudadano (Android; iOS sin probar)"]
        apk["«artifact»<br/>APK de Street Repo<br/><i>App Flutter: cámara, GPS, mapa</i>"]
    end

    subgraph pc["«device» Computador del funcionario"]
        nav["«execution environment»<br/>Navegador web<br/><i>SPA React del panel</i>"]
    end

    subgraph servidor["«execution environment» Servidor Linux con Docker Compose · red interna 172.30.0.0/24"]
        caddy["«container» caddy<br/>Caddy 2.11<br/><i>TLS Let's Encrypt, HSTS,<br/>tope de petición 11 MB / 1 MB</i><br/>puertos 80 y 443"]
        api["«container» api<br/>FastAPI + Uvicorn<br/><i>REST, JWT, motor de priorización</i><br/>puerto 8000"]
        adminweb["«container» admin-web<br/>nginx sin root<br/><i>build estático del panel, CSP</i><br/>puerto 8080"]
        migrate["«container» migrate<br/><i>alembic upgrade head<br/>(se ejecuta y termina)</i>"]
        db[("«container» db<br/>PostgreSQL 17 + PostGIS 3.5<br/>puerto 5432")]
        dbdata[("«volume» db-data")]
        photos[("«volume» photos<br/><i>fotos de evidencia</i>")]
    end

    subgraph vercel["«cloud» Vercel"]
        landing["«artifact»<br/>Página de presentación<br/><i>streetrepo.vercel.app</i>"]
    end

    subgraph osm["«cloud» OpenStreetMap"]
        tiles["«web service» Teselas"]
        overpass["«web service» Overpass API<br/><i>solo en osm-import</i>"]
    end

    apk -- "HTTPS REST + JWT<br/>API_DOMAIN" --> caddy
    nav -- "HTTPS<br/>PANEL_DOMAIN" --> caddy
    nav -- "HTTPS REST<br/>cookie HttpOnly + CSRF" --> caddy
    caddy -- "HTTP interno" --> api
    caddy -- "HTTP interno" --> adminweb
    migrate -- "TCP 5432" --> db
    api -- "TCP 5432" --> db
    db --- dbdata
    api -- "E/S de archivos" --> photos
    api -. "HTTPS (CLI osm-import)" .-> overpass
    apk -. "HTTPS" .-> tiles
    nav -. "HTTPS" .-> tiles
    pc -. "HTTPS" .-> landing
    telefono -. "descarga" .-> landing
```

Notas:

- En producción solo Caddy publica puertos; la base, la API y el panel quedan en la red interna, y
  la API solo cree `X-Forwarded-For` si viene de la IP fija de Caddy.
- En desarrollo (solo `docker-compose.yml`) no hay Caddy: la API se publica en el puerto 8000
  (`API_BIND_ADDRESS` permite exponerla en la red local para el celular) y el panel en el 8080.
- Los comandos de la CLI (`osm-import`, `zones-import`, `create-admin`, `create-evaluator`,
  `seed-demo`, `purge-orphan-photos`) se ejecutan dentro del contenedor `api`.
- La página de presentación se despliega aparte, en Vercel (decisión 99).
