import { Link, useLocation } from "react-router-dom";
import { ApiError } from "../../api/client";
import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import { useCurrentRound } from "./api";
import "./evaluation.css";

const LOAD_PROBLEM = "No pudimos cargar tus evaluaciones. Inténtalo de nuevo.";

/** Lo que deja la vista a ciegas al enviar una zona, para el aviso de éxito. */
export type SubmittedState = { submittedZone?: string };

/** Mis evaluaciones: las zonas de la ronda abierta y cuáles ya envió el evaluador. */
export function MyEvaluationsPage() {
  const current = useCurrentRound();
  const location = useLocation();
  const submittedZone = (location.state as SubmittedState | null)?.submittedZone;

  let body;
  if (current.isPending) {
    body = <LoadingView label="Cargando tus evaluaciones…" />;
  } else if (current.isError) {
    const message =
      current.error instanceof ApiError && current.error.code === "NETWORK_ERROR"
        ? current.error.message
        : LOAD_PROBLEM;
    body = <ErrorView message={message} onRetry={() => void current.refetch()} />;
  } else if (current.data === null) {
    body = (
      <EmptyView
        title="No hay una ronda de evaluación abierta"
        detail="Cuando el administrador abra una, aquí verás las zonas que debes ordenar."
      />
    );
  } else {
    const { round, zones } = current.data;
    const sent = zones.filter((zone) => zone.submitted).length;
    body = (
      <>
        <p className="page__subtitle">
          Ronda «{round.name}» · {sent} de {zones.length} zonas enviadas
        </p>
        <ul className="evaluation-zones" aria-label="Zonas por evaluar">
          {zones.map((zone) => (
            <li key={zone.id} className="card evaluation-zone">
              <div>
                <p className="evaluation-zone__name">{zone.name}</p>
                <p className="evaluation-zone__meta">{zone.n_reports} reportes</p>
              </div>
              <span
                className={`evaluation-chip evaluation-chip--${zone.submitted ? "sent" : "pending"}`}
              >
                {zone.submitted ? "Enviada" : "Pendiente"}
              </span>
              {zone.submitted ? null : (
                <Link
                  className="button"
                  to={`/evaluacion/zonas/${zone.id}`}
                  aria-label={`Ordenar la zona ${zone.name}`}
                >
                  Ordenar
                </Link>
              )}
            </li>
          ))}
        </ul>
      </>
    );
  }

  return (
    <div className="page">
      <header>
        <h1 className="page__title">Mis evaluaciones</h1>
        <p className="page__subtitle">
          Ordena los reportes de cada zona del más urgente al menos urgente, con lo que ves en la
          foto, la descripción y el mapa.
        </p>
      </header>
      {submittedZone ? (
        <p className="evaluation-notice" role="status">
          Enviaste el orden de la zona {submittedZone}. Gracias.
        </p>
      ) : null}
      {body}
    </div>
  );
}
