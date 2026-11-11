import type { ReportStatus, Severity } from "../api/types";

/** Formatos de la guía 9.2: español de Colombia, coma decimal y hora de Bogotá. */
const LOCALE = "es-CO";
const TIME_ZONE = "America/Bogota";
const SCORE_DECIMALS = 2;
const DISTANCE_DECIMALS = 1;

const scoreFormat = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: SCORE_DECIMALS,
  maximumFractionDigits: SCORE_DECIMALS,
});

const distanceFormat = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: DISTANCE_DECIMALS,
  maximumFractionDigits: DISTANCE_DECIMALS,
});

const dateTimeFormat = new Intl.DateTimeFormat(LOCALE, {
  timeZone: TIME_ZONE,
  day: "numeric",
  month: "short",
  hour: "numeric",
  minute: "2-digit",
  hourCycle: "h23",
});

const HOURS_PER_HALF_DAY = 12;

type DateParts = { day: string; month: string; hour: number; minute: string };

/**
 * Se arma a partir de las partes para no depender de los espacios ni de la abreviatura
 * («oct.», «p. m.» con espacios duros) que cada motor de JavaScript escribe distinto.
 */
function bogotaParts(iso: string): DateParts {
  const parts = new Map(dateTimeFormat.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
  return {
    day: parts.get("day") ?? "",
    month: (parts.get("month") ?? "").replace(".", ""),
    hour: Number(parts.get("hour")),
    minute: parts.get("minute") ?? "",
  };
}

/** Puntajes S, F, P y U: `8.7` → «8,70». */
export function formatScore(value: number): string {
  return scoreFormat.format(value);
}

/** Fecha corta: «13 oct». */
export function formatShortDate(iso: string): string {
  const { day, month } = bogotaParts(iso);
  return `${day} ${month}`;
}

/** Fecha y hora del historial: «13 oct, 4:05 p. m.». */
export function formatDateTime(iso: string): string {
  const { day, month, hour, minute } = bogotaParts(iso);
  const period = hour < HOURS_PER_HALF_DAY ? "a. m." : "p. m.";
  const hour12 = hour % HOURS_PER_HALF_DAY || HOURS_PER_HALF_DAY;
  return `${day} ${month}, ${hour12}:${minute} ${period}`;
}

/** Distancia en metros: `225.54` → «225,5 m». */
export function formatDistance(meters: number): string {
  return `${distanceFormat.format(meters)} m`;
}

const STATUS_LABELS: Record<ReportStatus, string> = {
  registrado: "Registrado",
  evaluado: "Evaluado",
  priorizado: "Priorizado",
  reparado: "Reparado",
};

const SEVERITY_LABELS: Record<Severity, string> = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
};

export function statusLabel(status: ReportStatus): string {
  return STATUS_LABELS[status];
}

export function severityLabel(severity: Severity): string {
  return SEVERITY_LABELS[severity];
}
