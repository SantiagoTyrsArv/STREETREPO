import type { ReportStatus } from "../api/types";
import { statusLabel } from "../format/format";

/** Estado del reporte; siempre con texto, nunca solo color (guía 10.3). */
export function StatusChip({ status }: { status: ReportStatus }) {
  return (
    <span className="chip" data-status={status}>
      {statusLabel(status)}
    </span>
  );
}
