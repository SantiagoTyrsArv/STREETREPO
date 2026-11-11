import type { RankingItem } from "./api";

/** Datos de ejemplo del diseño (guía 8.3), solo como fixtures. */
export const ESTUDIANTES: RankingItem = {
  id: "11111111-1111-4111-8111-111111111111",
  status: "evaluado",
  severity: "alta",
  s: 10,
  f: 7,
  p: 8,
  u: 8.7,
  needs_road_review: false,
  address: "Av. Los Estudiantes",
  confirmations: 3,
  created_at: "2026-10-13T21:05:00Z",
};

export const OBONUCO: RankingItem = {
  id: "66666666-6666-4666-8666-666666666666",
  status: "registrado",
  severity: "media",
  s: 6,
  f: 2,
  p: 0,
  u: 3.6,
  needs_road_review: true,
  address: "Sin vía asociada",
  confirmations: 1,
  created_at: "2026-10-14T15:00:00Z",
};
