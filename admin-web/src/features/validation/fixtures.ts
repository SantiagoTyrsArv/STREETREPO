/** Datos de prueba de la comparación (objetivo 4): ilustrativos, no son datos de campo. */
import type { Round, RoundProgress, RoundResults, Zone } from "./api";

const square = (lon: number, lat: number) => ({
  type: "Polygon",
  coordinates: [
    [
      [lon, lat],
      [lon + 0.01, lat],
      [lon + 0.01, lat + 0.01],
      [lon, lat + 0.01],
      [lon, lat],
    ],
  ],
});

export const ZONES: Zone[] = [
  {
    id: 1,
    name: "Centro",
    concentration: "alta",
    active_reports: 14,
    total_reports: 18,
    geometry: square(-77.285, 1.21),
  },
  {
    id: 2,
    name: "Obonuco",
    concentration: "baja",
    active_reports: 6,
    total_reports: 7,
    geometry: square(-77.3, 1.195),
  },
];

export const OPEN_ROUND: Round = {
  id: "r-2",
  name: "Piloto 2",
  status: "abierta",
  sample_size: 10,
  opened_at: "2026-11-20T15:00:00Z",
  closed_at: null,
};

export const CLOSED_ROUND: Round = {
  id: "r-1",
  name: "Piloto 1",
  status: "cerrada",
  sample_size: 8,
  opened_at: "2026-11-10T15:00:00Z",
  closed_at: "2026-11-12T20:00:00Z",
};

export const OPEN_PROGRESS: RoundProgress = {
  ...OPEN_ROUND,
  zones: [
    {
      zone_id: 1,
      name: "Centro",
      concentration: "alta",
      n_reports: 10,
      submitted_by: ["Evaluador 1"],
    },
    { zone_id: 2, name: "Obonuco", concentration: "baja", n_reports: 6, submitted_by: [] },
  ],
};

const report = (
  id: string,
  road: string | null,
  motor: number,
  panel: number | null,
): RoundResults["zones"][number]["reports"][number] => ({
  report_id: id,
  road_name: road,
  urgency_score: 9 - motor,
  motor_order: motor,
  panel_order: panel,
  disagreement: panel === null ? null : Math.abs(motor - panel) / 4,
  within_one: panel === null ? null : Math.abs(motor - panel) <= 1,
});

const DEDUP = {
  reports: 18,
  reports_confirmed: 6,
  confirmations: 9,
  warnings_total: 7,
  warnings_confirmed: 4,
  warnings_created_anyway: 2,
  warnings_pending: 1,
};

/** Ronda cerrada con dos zonas: Centro con dos evaluadores y Obonuco sin órdenes. */
export const RESULTS: RoundResults = {
  round: CLOSED_ROUND,
  zones: [
    {
      zone_id: 1,
      name: "Centro",
      concentration: "alta",
      n_reports: 5,
      agreement: {
        n_evaluators: 2,
        spearman: { coefficient: 0.8125, p_value: 0.0213 },
        kendall: { coefficient: 0.6, p_value: 0.045 },
        kendall_w: { w: 0.875, chi2: 7, p_value: 0.0719 },
        within_one_pct: 80,
        per_evaluator: [
          {
            evaluator: "Evaluador 1",
            spearman: { coefficient: 0.9, p_value: 0.037 },
            kendall: { coefficient: 0.8, p_value: 0.05 },
          },
          { evaluator: "Evaluador 2", spearman: null, kendall: null },
        ],
      },
      dedup: DEDUP,
      reports: [
        report("a", "Carrera 27", 1, 1.5),
        report("b", "Calle 18", 2, 4),
        report("c", null, 3, 1.5),
        report("d", "Calle 20", 4, 3),
        report("e", "Carrera 24", 5, 5),
      ],
    },
    {
      zone_id: 2,
      name: "Obonuco",
      concentration: "baja",
      n_reports: 5,
      agreement: null,
      dedup: { ...DEDUP, reports: 7, warnings_total: 0 },
      reports: [report("f", "Vía a Obonuco", 1, null)],
    },
  ],
  between: {
    computable: false,
    test: null,
    statistic: null,
    p_value: null,
    significant: null,
    reason: "Se necesita al menos una zona de alta y una de baja concentración con órdenes",
  },
};
