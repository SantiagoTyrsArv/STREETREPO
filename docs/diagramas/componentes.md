# Diagrama de componentes UML

Fuente canónica de la arquitectura. Refleja lo construido al 2026-11-23 (fila 130 de la bitácora):
un monolito modular en FastAPI con capas `presentation → application → domain ← infrastructure`
(sección 4 de `AGENTS.md`), dos clientes y la página de presentación.

```mermaid
flowchart TB
    subgraph clientes["Clientes"]
        app["«component»<br/>App ciudadana<br/><i>Flutter · Riverpod · go_router · dio<br/>cámara, GPS, mapa (flutter_map)</i>"]
        panel["«component»<br/>Panel administrativo<br/><i>React · TanStack Query · Leaflet + leaflet.heat<br/>roles administrador y evaluador</i>"]
        landing["«component»<br/>Página de presentación<br/><i>React (Vite) · GSAP · Lenis, prerenderizada</i>"]
    end

    iapi(("API REST /api/v1<br/>HTTPS · JSON<br/>JWT (app) · cookie HttpOnly + CSRF (panel)"))

    subgraph backend["Backend · FastAPI (monolito modular)"]
        core["«component» core<br/><i>config, logs JSON, errores uniformes,<br/>cabeceras de seguridad, límite de tamaño,<br/>límite de intentos, /health y /ready</i>"]
        auth["«component» auth<br/><i>registro con consentimiento, login Argon2id,<br/>JWT + refresco rotatorio, sesión web, RBAC</i>"]
        users["«component» users<br/><i>perfil, derechos del titular (Ley 1581),<br/>supresión por anonimización</i>"]
        reports["«component» reports<br/><i>crear reporte, fotos sin EXIF,<br/>posible duplicado (25 m), mis reportes, mapa público</i>"]
        confirmations["«component» confirmations<br/><i>confirmar a 50 m o menos, una por usuario</i>"]
        priority["«component» priority<br/><i>motor U = w1·S + w2·F + w3·P,<br/>pesos versionados, recálculo</i>"]
        roads["«component» roads<br/><i>vías OSM, map-matching a 30 m</i>"]
        services["«component» critical_services<br/><i>hospitales y escuelas, proximidad</i>"]
        admin["«component» admin<br/><i>ranking, mapa de calor, detalle y estado,<br/>pesos, carga OSM, datos de demostración</i>"]
        validation["«component» validation<br/><i>objetivo 4: zonas, rondas, vista a ciegas,<br/>métricas, CSV y avisos de duplicado</i>"]
        cli["«component» CLI<br/><i>osm-import, zones-import, create-admin,<br/>create-evaluator, seed-demo, purge-orphan-photos</i>"]
        infra["«component» Adaptadores de infraestructura<br/><i>repositorios SQLAlchemy + GeoAlchemy2,<br/>fotos con Pillow, cliente Overpass</i>"]
    end

    subgraph datos["Datos"]
        pg[("«component»<br/>PostgreSQL + PostGIS<br/><i>migraciones Alembic 0001–0009</i>")]
        fotos[("«component»<br/>Almacén de fotos<br/><i>volumen en disco</i>")]
    end

    overpass["«component»<br/>Overpass API (OSM)<br/><i>solo en la carga, no por solicitud</i>"]
    tiles["«component»<br/>Teselas de OpenStreetMap<br/><i>proveedor configurable</i>"]

    app --> iapi
    panel --> iapi
    app -. "mapa" .-> tiles
    panel -. "mapa" .-> tiles
    iapi --- core
    core --> auth & users & reports & confirmations & admin & validation

    reports -- "evalúa al crear" --> priority
    reports -- "registra aviso" --> validation
    confirmations -- "registra aviso" --> validation
    admin --> priority
    admin --> reports
    validation -- "pesos vigentes, orden" --> priority
    priority --> roads
    priority --> services
    users -- "borra fotos y textos" --> reports
    cli --> admin & validation & auth & reports

    auth & users & reports & confirmations & priority & roads & services & admin & validation -.-> infra
    infra -- "SQL parametrizado<br/>ST_DWithin, ST_Distance" --> pg
    infra -- "guarda y sirve fotos" --> fotos
    infra -- "HTTPS, solo en osm-import" --> overpass
```

Notas:

- Cada módulo del backend tiene las capas `presentation / application / domain / infrastructure`;
  el dominio no importa FastAPI ni SQL y define sus puertos (ver [`clases.md`](clases.md)). Las
  flechas entre módulos son dependencias a través de esos puertos, y cada módulo tiene sus propios
  adaptadores en `infrastructure/` (aquí agrupados en un solo nodo).
- Nominatim no se usa en el MVP: la dirección del reporte es el nombre de la vía asociada
  (propuesta 41). Overpass solo se consulta al cargar los datos de OSM (sección 3.1).
- La página de presentación no consume la API: solo ofrece la descarga de la app (decisión 99).
