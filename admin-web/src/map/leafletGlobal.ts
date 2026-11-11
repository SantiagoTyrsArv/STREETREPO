import * as L from "leaflet";

/**
 * `leaflet.markercluster` se distribuye como script clásico: busca Leaflet en `window.L` y le
 * añade sus clases. Este módulo debe importarse antes que el complemento. Se publica una copia
 * porque el espacio de nombres de un módulo no admite propiedades nuevas.
 */
export const globalLeaflet: typeof L = { ...L };

(window as unknown as { L: typeof L }).L = globalLeaflet;
