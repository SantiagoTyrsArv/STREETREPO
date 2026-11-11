import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { components } from "../../api/schema";
import type { ReportStatus } from "../../api/types";
import { useSession } from "../../auth/SessionProvider";

export type Summary = components["schemas"]["SummaryResponse"];
export type RankingItem = components["schemas"]["RankingItemResponse"];
export type Ranking = components["schemas"]["RankingResponse"];
export type HeatPoint = components["schemas"]["HeatPointResponse"];
type Heatmap = components["schemas"]["HeatmapResponse"];
export type WeightVersion = components["schemas"]["WeightVersionResponse"];

export const RANKING_PAGE_SIZE = 20;

/** Claves de consulta del panel; las pantallas de detalle y pesos las invalidan al guardar. */
export const adminKeys = {
  all: ["admin"] as const,
  summary: ["admin", "summary"] as const,
  ranking: (statuses: readonly ReportStatus[], page: number) =>
    ["admin", "ranking", statuses, page] as const,
  heatmap: ["admin", "heatmap"] as const,
  currentWeights: ["admin", "weights", "current"] as const,
};

export function useSummary() {
  const { api } = useSession();
  return useQuery({
    queryKey: adminKeys.summary,
    queryFn: () => api.get<Summary>("/api/v1/admin/summary"),
  });
}

type RankingFilter = {
  /** Vacío = los activos, que es lo que responde la API sin `status` (decisión 13). */
  statuses: readonly ReportStatus[];
  /** Página desde 0. */
  page: number;
};

export function useRanking({ statuses, page }: RankingFilter) {
  const { api } = useSession();
  return useQuery({
    queryKey: adminKeys.ranking(statuses, page),
    queryFn: () =>
      api.get<Ranking>("/api/v1/admin/ranking", {
        status: statuses,
        limit: RANKING_PAGE_SIZE,
        offset: page * RANKING_PAGE_SIZE,
      }),
    // Al cambiar de página se conserva la anterior a la vista hasta que llega la nueva.
    placeholderData: keepPreviousData,
  });
}

export function useHeatPoints() {
  const { api } = useSession();
  return useQuery({
    queryKey: adminKeys.heatmap,
    queryFn: async () => (await api.get<Heatmap>("/api/v1/admin/heatmap")).points,
  });
}

/** Versión de pesos vigente, para mostrar la fórmula con los valores reales. */
export function useCurrentWeights() {
  const { api } = useSession();
  return useQuery({
    queryKey: adminKeys.currentWeights,
    queryFn: () => api.get<WeightVersion>("/api/v1/admin/weights"),
  });
}
