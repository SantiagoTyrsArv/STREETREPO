# Diagrama de clases UML

Fuente canónica del modelo de dominio desde el 2026-11-23. Es la versión en Mermaid del diagrama de
clases de Lucid («Street Repo - Diagrama de Clases UML», última edición del 2026-10-15), con su
mismo contenido. Las diferencias con el código actual están en la sección final y no se aplicaron
al diagrama (protocolo 0.3 de `AGENTS.md`).

```mermaid
classDiagram
    direction LR

    class Usuario {
        -id: UUID
        -nombre: String
        -correo: String
        -passwordHash: String
        -rol: Rol
        -activo: boolean
        -aceptaPolitica: boolean
        -fechaAceptacion: DateTime
        -fechaRegistro: DateTime
        +autenticar() Token
        +cambiarPassword() void
    }
    class Ciudadano {
        +crearReporte(foto, sev) Reporte
        +consultarMisReportes() List
    }
    class Administrador {
        +cambiarEstado(r, e) void
        +ajustarPesos(c) void
        +consultarPanel() List
    }
    class Reporte {
        -id: UUID
        -ubicacion: Ubicacion
        -direccion: String
        -severidad: int
        -descripcion: String [0..1]
        -estado: EstadoReporte
        -puntajePrioridad: double
        -fechaCreacion: DateTime
        +registrar() void
        +cambiarEstado(e) void
        +adjuntarEvidencia(ev) void
        +buscarDuplicado() Reporte
        +confirmar(u) void
    }
    class EstadoReporte {
        <<enumeration>>
        REGISTRADO
        EVALUADO
        PRIORIZADO
        REPARADO
    }
    class Ubicacion {
        -latitud: double
        -longitud: double
        -srid: int = 4326
        +distanciaA(u) double
    }
    class Evidencia {
        -id: UUID
        -urlFoto: String
        -formato: String
        -tamanoBytes: int
        -fechaSubida: DateTime
    }
    class Confirmacion {
        -id: UUID
        -fecha: DateTime
    }
    class HistorialEstado {
        -id: long
        -estadoAnterior: EstadoReporte
        -estadoNuevo: EstadoReporte
        -observacion: String
        -fechaCambio: DateTime
    }
    class Zona {
        -id: int
        -nombre: String
        -geom: Polygon
        +contiene(u) boolean
        +contarReportes() int
    }
    class Via {
        -id: int
        -osmId: long
        -nombre: String
        -jerarquia: JerarquiaVial
        -factorFlujo: double
        +obtenerFlujo() double
    }
    class ServicioCritico {
        -id: int
        -osmId: long
        -nombre: String
        -tipo: TipoServicio
        -ubicacion: Ubicacion
        +distanciaA(u) double
    }
    class EvaluacionPrioridad {
        -id: long
        -s: double
        -f: double
        -p: double
        -u: double
        -distanciaServicioM: double
        -fechaCalculo: DateTime
        +esUrgente() boolean
    }
    class ConfiguracionPesos {
        -id: int
        -wSeveridad: double
        -wFlujo: double
        -wProximidad: double
        -vigente: boolean
        -fechaCreacion: DateTime
        +validarSuma() boolean
    }
    class MotorPriorizacion {
        -config: ConfiguracionPesos
        +calcular(r: Reporte) Evaluacion
        +calcularFlujo(v: Via) double
        +calcularProximidad(u) double
        +calcularSeveridad(s: int) double
    }
    class NominatimClient {
        -baseUrl: String
        +geocodificar(u) String
    }
    class OverpassClient {
        -baseUrl: String
        +obtenerServicios() List
    }

    note for Confirmacion "Única por (reporte, usuario)"

    Usuario <|-- Ciudadano
    Usuario <|-- Administrador
    Ciudadano "1" -- Reporte : crea
    Reporte *-- "1" Ubicacion
    Reporte *-- "1..*" Evidencia
    Reporte *-- "0..*" HistorialEstado
    Confirmacion "*" --> "1" Reporte : confirma
    Confirmacion "*" --> "1" Usuario : realiza
    Zona "1" -- Reporte
    Reporte "0..*" -- Via
    Reporte ..> EstadoReporte
    Reporte "1" -- EvaluacionPrioridad
    Administrador "1" -- HistorialEstado
    Administrador "1" -- ConfiguracionPesos
    EvaluacionPrioridad "0..*" -- ServicioCritico
    EvaluacionPrioridad "0..*" -- ConfiguracionPesos
    MotorPriorizacion ..> ConfiguracionPesos : pondera con
    MotorPriorizacion ..> EvaluacionPrioridad : genera
    MotorPriorizacion ..> ServicioCritico : mide distancia
    MotorPriorizacion ..> Via : lee flujo
    NominatimClient ..> Ubicacion : geocodifica
    OverpassClient ..> ServicioCritico : obtiene
```

## Diferencias conocidas con el código (pendientes de decisión)

El diagrama conserva el diseño de la tesis. El código evolucionó con decisiones registradas en la
bitácora; estas diferencias se deben decidir antes de cambiar el diagrama:

- **Objetivo 4 (decisión 115):** faltan `RondaEvaluacion`, `ReporteDeRonda`, `OrdenEvaluador`,
  `AvisoDuplicado` y el rol `Evaluador`; `Zona` no tiene `concentracion`.
- **Autenticación y titular (propuestas 8 a 10):** faltan `TokenRefresco`, `SolicitudSupresion` y
  `Usuario.versionPolitica`.
- **Confirmación (propuesta 112):** falta `Confirmacion.distanciaM`.
- **Arquitectura:** el código separa el dominio en módulos con casos de uso y repositorios
  (sección 4 de `AGENTS.md`); el motor está dividido en reglas por factor (`FactorRules`) y
  `ReportEvaluator`. Nominatim y Overpass no se consultan en tiempo de ejecución: los datos de OSM se
  cargan con `osm-import` (sección 3.1).
