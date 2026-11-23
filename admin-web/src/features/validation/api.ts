import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "../../api/schema";
import { useSession } from "../../auth/SessionProvider";

export type Zone = components["schemas"]["ZoneResponse"];
export type Concentration = components["schemas"]["Concentration"];
export type Round = components["schemas"]["RoundSummaryResponse"];
export type RoundProgress = components["schemas"]["RoundProgressResponse"];
type Zones = components["schemas"]["ZonesResponse"];
type Rounds = components["schemas"]["RoundsResponse"];
type RoundCreated = components["schemas"]["RoundCreatedResponse"];
export type OpenRoundRequest = components["schemas"]["OpenRoundRequest"];

const ROUNDS_PATH = "/api/v1/admin/evaluation-rounds";
/** Las rondas recientes caben en una página; el panel no pagina el historial. */
export const ROUNDS_PAGE_SIZE = 20;

/** Claves de consulta de la comparación; abrir o cerrar una ronda invalida `["rounds"]`. */
export const validationKeys = {
  zones: ["validation", "zones"] as const,
  rounds: ["rounds"] as const,
  round: (id: string) => ["rounds", id] as const,
};

export function useZones() {
  const { api } = useSession();
  return useQuery({
    queryKey: validationKeys.zones,
    queryFn: async () => (await api.get<Zones>("/api/v1/admin/zones")).items,
  });
}

export function useRounds() {
  const { api } = useSession();
  return useQuery({
    queryKey: validationKeys.rounds,
    queryFn: async () =>
      (await api.get<Rounds>(ROUNDS_PATH, { limit: ROUNDS_PAGE_SIZE, offset: 0 })).items,
  });
}

export function useRound(id: string | undefined) {
  const { api } = useSession();
  return useQuery({
    queryKey: validationKeys.round(id ?? ""),
    queryFn: () => api.get<RoundProgress>(`${ROUNDS_PATH}/${id}`),
    enabled: id !== undefined,
  });
}

function useInvalidateRounds() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: validationKeys.rounds });
}

export function useOpenRound() {
  const { api } = useSession();
  const invalidate = useInvalidateRounds();
  return useMutation({
    mutationFn: (request: OpenRoundRequest) => api.post<RoundCreated>(ROUNDS_PATH, request),
    onSuccess: invalidate,
  });
}

export function useCloseRound(id: string) {
  const { api } = useSession();
  const invalidate = useInvalidateRounds();
  return useMutation({
    mutationFn: () => api.post<Round>(`${ROUNDS_PATH}/${id}/close`),
    onSuccess: invalidate,
  });
}
