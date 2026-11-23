import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../../api/client";
import type { components } from "../../api/schema";
import { useSession } from "../../auth/SessionProvider";

export type CurrentRound = components["schemas"]["CurrentRoundResponse"];
export type ZoneCards = components["schemas"]["ZoneCardsResponse"];
export type BlindCard = components["schemas"]["BlindCardResponse"];
export type ServicePoint = components["schemas"]["ServicePointResponse"];
type OrderSubmitted = components["schemas"]["OrderSubmittedResponse"];

const CURRENT_PATH = "/api/v1/evaluation/current";
const NO_OPEN_ROUND = "EVALUATION_NO_OPEN_ROUND";

export const evaluationKeys = {
  all: ["evaluation"] as const,
  current: ["evaluation", "current"] as const,
  zone: (zoneId: number) => ["evaluation", "zone", zoneId] as const,
};

export function photoPath(reportId: string, size: "thumbnail" | "full"): string {
  const base = `${CURRENT_PATH}/reports/${reportId}/photo`;
  return size === "thumbnail" ? `${base}/thumbnail` : base;
}

/** Ronda abierta y las zonas del evaluador; `null` si no hay una ronda abierta. */
export function useCurrentRound() {
  const { api } = useSession();
  return useQuery({
    queryKey: evaluationKeys.current,
    queryFn: async () => {
      try {
        return await api.get<CurrentRound>(CURRENT_PATH);
      } catch (error) {
        if (error instanceof ApiError && error.code === NO_OPEN_ROUND) {
          return null;
        }
        throw error;
      }
    },
  });
}

export function useZoneCards(zoneId: number) {
  const { api } = useSession();
  return useQuery({
    queryKey: evaluationKeys.zone(zoneId),
    queryFn: () => api.get<ZoneCards>(`${CURRENT_PATH}/zones/${zoneId}`),
    // El orden lo arma la persona: que una recarga en segundo plano no lo mueva.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
}

export function useSubmitOrder(zoneId: number) {
  const { api } = useSession();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reportIds: readonly string[]) =>
      api.put<OrderSubmitted>(`${CURRENT_PATH}/zones/${zoneId}/order`, {
        report_ids: reportIds,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: evaluationKeys.all }),
  });
}
