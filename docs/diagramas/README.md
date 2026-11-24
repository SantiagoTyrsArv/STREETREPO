# Diagramas

Desde el 2026-11-23 los diagramas del proyecto viven aquí, en Mermaid, versionados con el código
(fila 129 de la bitácora). Reemplazan a los de Lucid, que quedan como respaldo histórico: el DER de
Lucid dejó de ser editable y no reflejaba las migraciones 0008 y 0009.

| Diagrama | Archivo | Qué describe |
|---|---|---|
| Entidad-relación | [`er.md`](er.md) | Esquema real de la base (migraciones 0001 a 0009) |
| Clases UML | [`clases.md`](clases.md) | Modelo de dominio, motor de priorización y casos de uso |
| Componentes UML | [`componentes.md`](componentes.md) | Módulos del sistema y sus dependencias |
| Despliegue UML | [`despliegue.md`](despliegue.md) | Nodos, contenedores y protocolos |

Los cuatro reflejan lo construido (fila 130 de la bitácora). Las versiones de Lucid eran el diseño
inicial de la tesis; quedan en el historial de git (commit `a9cee2e`) y en Lucid como respaldo.

## Ver y exportar

- GitHub y VS Code (con soporte de Mermaid) los muestran directamente.
- En [Mermaid Chart](https://www.mermaidchart.com/) o en el [editor en línea](https://mermaid.live/)
  se pega el bloque `mermaid` de cada archivo.
- Para la tesis, exportar a SVG o PNG con Mermaid CLI:

  ```bash
  npx -p @mermaid-js/mermaid-cli mmdc -i docs/diagramas/er.md -o er.svg
  ```

Al cambiar el esquema (nueva migración) se actualiza `er.md` en la misma rama.
