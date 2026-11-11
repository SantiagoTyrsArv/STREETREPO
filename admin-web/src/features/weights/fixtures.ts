import type { WeightVersion } from "./api";

export const INITIAL_VERSION: WeightVersion = {
  id: 1,
  w_severity: 0.5,
  w_flow: 0.3,
  w_proximity: 0.2,
  created_at: "2026-10-12T15:00:00Z",
  created_by_name: null,
  is_current: false,
};

export const CURRENT_VERSION: WeightVersion = {
  id: 4,
  w_severity: 0.5,
  w_flow: 0.3,
  w_proximity: 0.2,
  created_at: "2026-10-13T21:05:00Z",
  created_by_name: "Ana Funcionaria",
  is_current: true,
};
