import type { Severity } from "../api/types";
import { severityLabel } from "../format/format";

/** Severidad declarada por el ciudadano; siempre con texto (guía 10.3). */
export function SeverityChip({ severity }: { severity: Severity }) {
  return (
    <span className="chip" data-severity={severity}>
      {severityLabel(severity)}
    </span>
  );
}
