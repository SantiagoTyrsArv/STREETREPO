import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "../../api/schema";
import type { ReportStatus } from "../../api/types";
import { useSession } from "../../auth/SessionProvider";
import { adminKeys } from "../prioritization/api";

export type AdminReport = components["schemas"]["AdminReportResponse"];
export type Evaluation = components["schemas"]["EvaluationResponse"];
export type HistoryEntry = components["schemas"]["AdminHistoryEntryResponse"];

export const reportKey = (id: string) => ["admin", "report", id] as const;

export function useAdminReport(id: string) {
  const { api } = useSession();
  return useQuery({
    queryKey: reportKey(id),
    queryFn: () => api.get<AdminReport>(`/api/v1/admin/reports/${id}`),
  });
}

type StatusChange = { status: ReportStatus; note: string | null };

/** Cambia el estado (HU-12) y refresca lo que depende de él: detalle, ranking, resumen y mapa. */
export function useChangeStatus(id: string) {
  const { api } = useSession();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (change: StatusChange) =>
      api.patch<AdminReport>(`/api/v1/admin/reports/${id}/status`, change),
    onSuccess: (report) => {
      // La API responde el detalle ya actualizado.
      queryClient.setQueryData(reportKey(id), report);
      void queryClient.invalidateQueries({ queryKey: ["admin", "ranking"] });
      void queryClient.invalidateQueries({ queryKey: adminKeys.summary });
      void queryClient.invalidateQueries({ queryKey: adminKeys.heatmap });
    },
  });
}
