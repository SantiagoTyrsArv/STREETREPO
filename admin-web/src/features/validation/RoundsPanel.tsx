import { useId, useState } from "react";
import { ApiError } from "../../api/client";
import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import { formatDateTime } from "../../format/format";
import { useCloseRound, useRound, useRounds, type Round } from "./api";
import { concentrationLabel, roundStatusLabel } from "./labels";
import { OpenRoundForm } from "./OpenRoundForm";

const LOAD_PROBLEM = "No pudimos cargar las rondas. Inténtalo de nuevo.";
const CLOSE_PROBLEM = "No pudimos cerrar la ronda. Inténtalo de nuevo.";

function CloseRound({ round }: { round: Round }) {
  const titleId = useId();
  const [confirming, setConfirming] = useState(false);
  const close = useCloseRound(round.id);

  if (!confirming) {
    return (
      <button type="button" className="button button--outline" onClick={() => setConfirming(true)}>
        Cerrar ronda
      </button>
    );
  }
  return (
    <div className="close-round" role="group" aria-labelledby={titleId}>
      <p id={titleId} className="close-round__title">
        Confirmar el cierre
      </p>
      <p>
        ¿Cerrar la ronda «{round.name}»? Ya no se aceptarán órdenes de los evaluadores y se
        calcularán los resultados.
      </p>
      {close.isError ? (
        <div className="alert" role="alert">
          <span className="alert__icon" aria-hidden="true">
            !
          </span>
          <p>{close.error instanceof ApiError ? close.error.message : CLOSE_PROBLEM}</p>
        </div>
      ) : null}
      <div className="close-round__actions">
        <button
          type="button"
          className="button"
          disabled={close.isPending}
          onClick={() => close.mutate()}
        >
          {close.isPending ? "Cerrando…" : "Sí, cerrar la ronda"}
        </button>
        <button
          type="button"
          className="button button--secondary"
          disabled={close.isPending}
          onClick={() => {
            close.reset();
            setConfirming(false);
          }}
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}

/** Avance de la ronda abierta: qué evaluador envió cada zona. Las métricas no se ven aquí. */
function OpenRoundProgress({ round }: { round: Round }) {
  const progress = useRound(round.id);

  let body;
  if (progress.isPending) {
    body = <LoadingView label="Cargando el avance…" />;
  } else if (progress.isError) {
    body = <ErrorView message={LOAD_PROBLEM} onRetry={() => void progress.refetch()} />;
  } else {
    body = (
      <table className="data-table" aria-label={`Avance de la ronda «${round.name}»`}>
        <thead>
          <tr>
            <th scope="col">Zona</th>
            <th scope="col">Concentración</th>
            <th scope="col" className="data-table__number">
              Reportes
            </th>
            <th scope="col">Enviaron su orden</th>
          </tr>
        </thead>
        <tbody>
          {progress.data.zones.map((zone) => (
            <tr key={zone.zone_id}>
              <td>{zone.name}</td>
              <td>{concentrationLabel(zone.concentration)}</td>
              <td className="data-table__number">{zone.n_reports}</td>
              <td>
                {zone.submitted_by.length > 0
                  ? zone.submitted_by.join(", ")
                  : "Ningún evaluador todavía"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <section className="card">
      <div className="card__header">
        <div>
          <h2 className="card__title validation-title">Ronda abierta: {round.name}</h2>
          <p className="card__hint">
            Abierta el {formatDateTime(round.opened_at)} · hasta {round.sample_size} reportes por
            zona. Los resultados se calculan al cerrarla.
          </p>
        </div>
        <CloseRound round={round} />
      </div>
      {body}
    </section>
  );
}

function RoundsHistory({ rounds }: { rounds: readonly Round[] }) {
  if (rounds.length === 0) {
    return null;
  }
  return (
    <section className="card">
      <table className="data-table" aria-label="Rondas anteriores">
        <thead>
          <tr>
            <th scope="col">Ronda</th>
            <th scope="col">Estado</th>
            <th scope="col">Apertura</th>
            <th scope="col">Cierre</th>
          </tr>
        </thead>
        <tbody>
          {rounds.map((round) => (
            <tr key={round.id}>
              <td>{round.name}</td>
              <td>{roundStatusLabel(round.status)}</td>
              <td>{formatDateTime(round.opened_at)}</td>
              <td>{round.closed_at ? formatDateTime(round.closed_at) : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/** Rondas de evaluación: abrir (si no hay una abierta), seguir el avance y cerrar. */
export function RoundsPanel() {
  const rounds = useRounds();

  if (rounds.isPending) {
    return <LoadingView label="Cargando las rondas…" />;
  }
  if (rounds.isError) {
    return <ErrorView message={LOAD_PROBLEM} onRetry={() => void rounds.refetch()} />;
  }
  const open = rounds.data.find((round) => round.status === "abierta");
  const past = rounds.data.filter((round) => round !== open);

  return (
    <div className="rounds">
      {open ? <OpenRoundProgress round={open} /> : <OpenRoundForm />}
      {rounds.data.length === 0 ? (
        <EmptyView
          title="Aún no hay rondas"
          detail="Abre la primera cuando las zonas tengan sus reportes."
        />
      ) : null}
      <RoundsHistory rounds={past} />
    </div>
  );
}
