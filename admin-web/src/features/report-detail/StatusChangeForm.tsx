import { useId, useState, type FormEvent } from "react";
import { ApiError } from "../../api/client";
import type { ReportStatus } from "../../api/types";
import { statusLabel } from "../../format/format";
import { useChangeStatus } from "./api";

/** Mismo tope que valida la API (`NOTE_MAX_LENGTH`). */
const NOTE_MAX_LENGTH = 1000;
const HTTP_CONFLICT = 409;

type Props = {
  reportId: string;
  /** Transiciones que permite la máquina de estados del servidor (`allowed_next_statuses`). */
  allowedStatuses: readonly ReportStatus[];
  /** Otro administrador cambió el reporte: quien usa el formulario recarga el detalle. */
  onConflict?: () => void;
};

/** Cambio de estado con observación (HU-12). Las opciones las decide la API, no el panel. */
export function StatusChangeForm({ reportId, allowedStatuses, onConflict }: Props) {
  const change = useChangeStatus(reportId);
  const [selected, setSelected] = useState<ReportStatus | null>(null);
  const [note, setNote] = useState("");
  const [saved, setSaved] = useState(false);
  const noteId = useId();
  const groupName = useId();

  if (allowedStatuses.length === 0) {
    return <p className="status-form__closed">Este reporte no admite más cambios de estado.</p>;
  }

  // Si el detalle se recargó y el estado elegido ya no está permitido, la selección se descarta.
  const status = selected !== null && allowedStatuses.includes(selected) ? selected : null;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (status === null || change.isPending) {
      return;
    }
    setSaved(false);
    change.mutate(
      { status, note: note.trim() || null },
      {
        onSuccess: () => {
          setSelected(null);
          setNote("");
          setSaved(true);
        },
        onError: (error) => {
          if (error instanceof ApiError && error.status === HTTP_CONFLICT) {
            onConflict?.();
          }
        },
      },
    );
  }

  return (
    <form className="status-form" onSubmit={handleSubmit}>
      <fieldset className="status-form__options">
        <legend className="visually-hidden">Nuevo estado</legend>
        {allowedStatuses.map((option) => (
          <label key={option} className="status-form__option">
            <input
              type="radio"
              name={groupName}
              value={option}
              checked={status === option}
              onChange={() => {
                setSelected(option);
                setSaved(false);
              }}
            />
            <span>{statusLabel(option)}</span>
          </label>
        ))}
      </fieldset>

      <div className="status-form__note">
        <label htmlFor={noteId}>Observación (queda en el historial)</label>
        <textarea
          id={noteId}
          rows={2}
          maxLength={NOTE_MAX_LENGTH}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
        <span className="status-form__counter">
          {note.length}/{NOTE_MAX_LENGTH}
        </span>
      </div>

      {change.isError ? (
        <div className="alert" role="alert">
          <span className="alert__icon" aria-hidden="true">
            !
          </span>
          <p>{change.error.message}</p>
        </div>
      ) : null}
      {saved ? (
        <p className="status-form__saved" role="status">
          Estado actualizado.
        </p>
      ) : null}

      <button type="submit" className="button" disabled={status === null || change.isPending}>
        {change.isPending ? "Guardando…" : "Guardar cambio"}
      </button>
    </form>
  );
}
