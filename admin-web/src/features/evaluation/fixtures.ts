/** Datos de prueba de la vista a ciegas: ilustrativos, no son datos de campo. */
import type { CurrentRound, ZoneCards } from "./api";

export const CURRENT_ROUND: CurrentRound = {
  round: { id: "r-1", name: "Piloto 1" },
  zones: [
    { id: 1, name: "Centro", n_reports: 3, submitted: false },
    { id: 2, name: "Obonuco", n_reports: 5, submitted: true },
  ],
};

export const CENTRO_CARDS: ZoneCards = {
  zone: { id: 1, name: "Centro", n_reports: 3 },
  submitted: false,
  cards: [
    {
      report_id: "a",
      description: "Hueco profundo frente al colegio",
      road_name: "Carrera 27",
      severity: "alta",
      location: { longitude: -77.281, latitude: 1.213 },
      nearby_services: [
        {
          name: "I. E. M. Ciudad de Pasto",
          type: "escuela",
          location: { longitude: -77.282, latitude: 1.214 },
        },
      ],
    },
    {
      report_id: "b",
      description: null,
      road_name: "Calle 18",
      severity: "media",
      location: { longitude: -77.28, latitude: 1.212 },
      nearby_services: [],
    },
    {
      report_id: "c",
      description: "Grieta",
      road_name: null,
      severity: "baja",
      location: { longitude: -77.279, latitude: 1.211 },
      nearby_services: [],
    },
  ],
};
