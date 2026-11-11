import { useId, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, NETWORK_ERROR_MESSAGE } from "../../api/client";
import iconBack from "../../assets/icon-back.svg";
import iconUsers from "../../assets/icon-users.svg";
import { AuthImage } from "../../components/AuthImage";
import { ReviewRoadChip } from "../../components/ReviewRoadChip";
import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import { StatusChip } from "../../components/StatusChip";
import { formatShortDate, severityLabel } from "../../format/format";
import { useAdminReport, type AdminReport } from "./api";
import { HistoryList } from "./HistoryList";
import { confirmationsSentence, highwayLabel } from "./labels";
import { LocationMap } from "./LocationMap";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { StatusChangeForm } from "./StatusChangeForm";
import "./report-detail.css";

const HTTP_NOT_FOUND = 404;
const SERVER_PROBLEM = "Hubo un problema al consultar el servidor. Inténtalo de nuevo.";

function BackLink() {
  return (
    <Link to="/priorizacion" className="back-link">
      <img src={iconBack} alt="" width={18} height={18} />
      Volver al ranking
    </Link>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  const titleId = useId();
  return (
    <section className="card detail-card" aria-labelledby={titleId}>
      <h2 id={titleId} className="card__title">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <p className="fact">
      <strong>{label}: </strong>
      <span>{children}</span>
    </p>
  );
}

function Detail({ report, onConflict }: { report: AdminReport; onConflict: () => void }) {
  return (
    <>
      <header className="detail-header">
        <BackLink />
        <div className="detail-header__title">
          <h1 className="page__title">{report.address}</h1>
          <StatusChip status={report.status} />
        </div>
        <p className="page__subtitle">
          Reportado el {formatShortDate(report.created_at)} por {report.reporter_name} · Severidad{" "}
          {severityLabel(report.severity).toLowerCase()}
        </p>
      </header>

      <div className="detail-columns">
        <div className="detail-column">
          <Card title="Evidencia">
            <AuthImage
              src={`/api/v1/reports/${report.id}/photo`}
              alt="Foto del daño"
              className="detail-photo"
            />
          </Card>

          <Card title="Ubicación y vía">
            <LocationMap lat={report.location.lat} lon={report.location.lon} />
            <div className="facts">
              {report.road ? (
                <>
                  <Fact label="Vía OSM">{report.road.name ?? report.address}</Fact>
                  <Fact label="Jerarquía">{highwayLabel(report.road.highway)}</Fact>
                </>
              ) : (
                <>
                  <p className="fact">Sin vía asociada</p>
                  <ReviewRoadChip />
                </>
              )}
            </div>
            {report.description ? (
              <p className="detail-description">“{report.description}”</p>
            ) : null}
            <p className="detail-confirmations">
              <img src={iconUsers} alt="" width={18} height={18} />
              {confirmationsSentence(report.confirmations)}
            </p>
          </Card>
        </div>

        <div className="detail-column">
          <Card title="Cálculo de prioridad">
            <ScoreBreakdown
              evaluation={report.evaluation}
              severity={report.severity}
              road={report.road}
            />
          </Card>

          <Card title="Cambiar estado">
            <StatusChangeForm
              reportId={report.id}
              allowedStatuses={report.allowed_next_statuses}
              onConflict={onConflict}
            />
          </Card>

          <Card title="Historial de estados">
            <HistoryList entries={report.history} />
          </Card>
        </div>
      </div>
    </>
  );
}

/** Detalle y estado (HU-12): evidencia, vía, desglose del cálculo, cambio de estado e historial. */
export function ReportDetailPage() {
  const { id = "" } = useParams();
  const report = useAdminReport(id);

  if (report.isPending) {
    return (
      <div className="page">
        <LoadingView label="Cargando el reporte…" />
      </div>
    );
  }
  if (report.isError) {
    const { error } = report;
    const notFound = error instanceof ApiError && error.status === HTTP_NOT_FOUND;
    return (
      <div className="page">
        <BackLink />
        {notFound ? (
          <EmptyView
            title="No encontramos este reporte"
            detail="Puede que el enlace esté incompleto o que el reporte ya no exista."
          />
        ) : (
          <ErrorView
            title="No pudimos cargar el reporte"
            message={
              error instanceof ApiError && error.code === "NETWORK_ERROR"
                ? NETWORK_ERROR_MESSAGE
                : SERVER_PROBLEM
            }
            onRetry={() => void report.refetch()}
          />
        )}
      </div>
    );
  }
  return (
    <div className="page">
      <Detail report={report.data} onConflict={() => void report.refetch()} />
    </div>
  );
}
