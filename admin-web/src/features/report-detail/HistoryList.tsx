import { formatDateTime, statusLabel } from "../../format/format";
import type { HistoryEntry } from "./api";

/** Sin autor, el cambio lo hizo el motor de priorización (o la cuenta fue suprimida). */
const SYSTEM_AUTHOR = "Sistema";

function transition(entry: HistoryEntry): string {
  return entry.previous_status
    ? `${statusLabel(entry.previous_status)} → ${statusLabel(entry.status)}`
    : statusLabel(entry.status);
}

/** Historial de estados en el orden que entrega la API. */
export function HistoryList({ entries }: { entries: readonly HistoryEntry[] }) {
  return (
    <ol className="history">
      {entries.map((entry) => (
        <li key={`${entry.changed_at}-${entry.status}`} className="history__item">
          <span className="history__dot" data-status={entry.status} aria-hidden="true" />
          <div>
            <p className="history__title">{transition(entry)}</p>
            <p className="history__meta">
              {formatDateTime(entry.changed_at)} · {entry.changed_by_name ?? SYSTEM_AUTHOR}
            </p>
            {entry.note ? <p className="history__note">«{entry.note}»</p> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
