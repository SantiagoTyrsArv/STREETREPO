import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "../../api/schema";
import { useSession } from "../../auth/SessionProvider";
import { adminKeys, useCurrentWeights, type WeightVersion } from "../prioritization/api";

export { useCurrentWeights };
export type { WeightVersion };
type WeightVersions = components["schemas"]["WeightVersionsResponse"];
export type WeightsSaved = components["schemas"]["WeightsSavedResponse"];

export const VERSIONS_PAGE_SIZE = 20;
/** Prefijo de todas las consultas de pesos (vigente y versiones). */
const WEIGHTS_KEY = ["admin", "weights"] as const;

export function useWeightVersions(page: number) {
  const { api } = useSession();
  return useQuery({
    queryKey: [...WEIGHTS_KEY, "versions", page] as const,
    queryFn: () =>
      api.get<WeightVersions>("/api/v1/admin/weights/versions", {
        limit: VERSIONS_PAGE_SIZE,
        offset: page * VERSIONS_PAGE_SIZE,
      }),
  });
}

/** Pesos como cadenas con punto y dos decimales, para que viajen sin perder precisión. */
export type WeightsInput = { w_severity: string; w_flow: string; w_proximity: string };

type SaveRequest = WeightsInput & {
  /** Versión sobre la que se editó; si ya no es la vigente, la API responde 409. */
  base_version_id: number;
};

/** Guarda una versión nueva (HU-14). El servidor recalcula los reportes activos. */
export function useSaveWeights() {
  const { api } = useSession();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: SaveRequest) => api.put<WeightsSaved>("/api/v1/admin/weights", request),
    onSuccess: (saved) => {
      queryClient.setQueryData(adminKeys.currentWeights, saved.version);
      // Con pesos nuevos cambia todo lo que muestra U.
      for (const queryKey of [
        WEIGHTS_KEY,
        ["admin", "ranking"],
        adminKeys.summary,
        adminKeys.heatmap,
        ["admin", "report"],
      ]) {
        void queryClient.invalidateQueries({ queryKey });
      }
    },
  });
}

/** Vuelve a pedir la versión vigente y la lista de versiones. */
export function useReloadWeights() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: WEIGHTS_KEY });
}
