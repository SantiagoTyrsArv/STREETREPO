# Diagrama de componentes UML

Fuente canónica desde el 2026-11-23. Es la versión en Mermaid del diagrama de componentes de Lucid
(«Street Repo - Diagrama de Componentes UML», última edición del 2026-10-15), con su mismo
contenido. Las diferencias con el sistema construido están en la sección final.

```mermaid
flowchart TB
    subgraph presentacion["Capa de presentación (clientes)"]
        app["«component»<br/>App Móvil Ciudadana<br/><i>Flutter: cámara, GPS, formulario de reporte</i>"]
        panel["«component»<br/>Panel Administrativo<br/><i>React + Leaflet: mapa y gestión de estados</i>"]
    end

    iapi(("IApiREST<br/>HTTPS/JSON + JWT"))

    subgraph backend["Backend - API REST (FastAPI, Docker)"]
        router["«component»<br/>Controladores REST<br/><i>routers FastAPI, validación Pydantic</i>"]
        auth["«component»<br/>Módulo de Autenticación<br/><i>JWT, roles ciudadano/admin</i>"]
        rep["«component»<br/>Módulo de Reportes<br/><i>registro, consulta, estados</i>"]
        evid["«component»<br/>Módulo de Evidencias<br/><i>carga y validación de fotos</i>"]
        prior["«component»<br/>Motor de Priorización<br/><i>U = w1·S + w2·F + w3·P</i>"]
        datos["«component»<br/>Acceso a Datos<br/><i>SQLAlchemy + GeoAlchemy2: ST_Distance, ST_DWithin</i>"]
        nomc["«component»<br/>Cliente Nominatim<br/><i>geocodificación inversa</i>"]
        ovc["«component»<br/>Cliente Overpass<br/><i>hospitales y colegios</i>"]
    end

    subgraph capaDatos["Capa de datos (Docker)"]
        pg[("«component»<br/>PostgreSQL + PostGIS<br/><i>reportes, vías, zonas, servicios</i>")]
        alm[("«component»<br/>Almacén de Evidencias<br/><i>volumen de archivos (fotos)</i>")]
    end

    subgraph externos["Servicios externos (OpenStreetMap)"]
        nomapi["«component»<br/>Nominatim API<br/><i>geocodificación</i>"]
        ovapi["«component»<br/>Overpass API<br/><i>consulta de datos OSM</i>"]
    end

    app --> iapi
    panel --> iapi
    iapi --- router
    router --> auth
    router --> rep
    router --> evid
    router --> prior
    rep -- "solicita puntaje" --> prior
    rep --> datos
    rep --> nomc
    prior --> ovc
    prior --> datos
    auth --> datos
    evid -- "guarda fotos" --> alm
    datos -- "SQL / PostGIS" --> pg
    nomc -- "HTTPS" --> nomapi
    ovc -- "HTTPS" --> ovapi
```

## Diferencias conocidas con el sistema construido (pendientes de decisión)

- El backend es un monolito modular con módulos `auth`, `users`, `reports`, `confirmations`,
  `priority`, `roads`, `critical_services`, `admin` y `validation` (zonas, rondas y avisos del
  objetivo 4), cada uno con capas `presentation / application / domain / infrastructure`.
- Nominatim y Overpass no se llaman en tiempo de ejecución: la carga de OSM es un comando aparte
  (`osm-import`) que guarda vías y servicios en PostGIS (sección 3.1 de `AGENTS.md`); la dirección
  del reporte es el nombre de la vía (propuesta 41).
- Existe una tercera interfaz cliente: la página de presentación (`landing/`, en Vercel, decisión 99).
