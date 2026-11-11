import type { components } from "./schema";

/** Alias sobre el contrato generado (`npm run gen:api`); el panel no define estados propios. */
export type ReportStatus = components["schemas"]["ReportStatus"];
export type Severity = components["schemas"]["SeverityLevel"];
