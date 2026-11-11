import { useId, useState } from "react";
import { ApiError } from "../../api/client";
import type { ReportStatus } from "../../api/types";
import { Pagination } from "../../components/Pagination";
import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import { formatWeight } from "../../format/format";
import {
  RANKING_PAGE_SIZE,
  useCurrentWeights,
  useHeatPoints,
  useRanking,
  useSummary,
  type WeightVersion,
} from "./api";
import { HeatLegend } from "./HeatLegend";
import { HeatMap } from "./HeatMap";
import { RankingTable } from "./RankingTable";
import { SummaryCards } from "./SummaryCards";
import "./prioritization.css";

type FilterKey = "activos" | "todos" | ReportStatus;

/** Filtro por estado. «Activos» no envía `status`: es el valor por defecto de la API. */
const FILTERS: ReadonlyArray<{
  key: FilterKey;
  label: string;
  statuses: readonly ReportStatus[];
}> = [
  { key: "activos", label: "Estado: activos", statuses: [] },
  { key: "registrado", label: "Estado: registrados", statuses: ["registrado"] },
  { key: "evaluado", label: "Estado: evaluados", statuses: ["evaluado"] },
  { key: "priorizado", label: "Estado: priorizados", statuses: ["priorizado"] },
  { key: "reparado", label: "Estado: reparados", statuses: ["reparado"] },
  {
    key: "todos",
    label: "Estado: todos",
    statuses: ["registrado", "evaluado", "priorizado", "reparado"],
  },
];
const DEFAULT_FILTER = FILTERS[0]!;

const SERVER_PROBLEM = "Hubo un problema al consultar el servidor. Inténtalo de nuevo.";

/** Los fallos de red traen su propia explicación; el resto usa el texto del diseño. */
function problemDetail(error: unknown): string {
  return error instanceof ApiError && error.code === "NETWORK_ERROR"
    ? error.message
    : SERVER_PROBLEM;
}

function formula(weights: WeightVersion | undefined): string {
  if (!weights) {
    return "Ranking por urgencia U (pesos vigentes)";
  }
  const { w_severity: w1, w_flow: w2, w_proximity: w3 } = weights;
  return `Ranking por urgencia U = ${formatWeight(w1)}·S + ${formatWeight(w2)}·F + ${formatWeight(w3)}·P (pesos vigentes)`;
}

/** Priorización (HU-08): indicadores, mapa de calor y ranking, tal como los entrega la API. */
export function PrioritizationPage() {
  const [filterKey, setFilterKey] = useState<FilterKey>(DEFAULT_FILTER.key);
  const [page, setPage] = useState(0);
  const [showReports, setShowReports] = useState(false);
  const filterId = useId();
  const filter = FILTERS.find((option) => option.key === filterKey) ?? DEFAULT_FILTER;

  const summary = useSummary();
  const weights = useCurrentWeights();
  const heat = useHeatPoints();
  const ranking = useRanking({ statuses: filter.statuses, page });

  function changeFilter(key: string) {
    setFilterKey(key as FilterKey);
    setPage(0);
  }

  let rankingBody;
  if (ranking.isPending) {
    rankingBody = <LoadingView label="Cargando el ranking…" />;
  } else if (ranking.isError) {
    rankingBody = (
      <ErrorView
        title="No pudimos cargar el ranking"
        message={problemDetail(ranking.error)}
        onRetry={() => void ranking.refetch()}
      />
    );
  } else if (ranking.data.total === 0) {
    rankingBody =
      filter.key === DEFAULT_FILTER.key ? (
        <EmptyView
          mark="0"
          title="Aún no hay reportes"
          detail="Cuando los ciudadanos envíen reportes aparecerán aquí, ordenados por urgencia."
        />
      ) : (
        <EmptyView mark="0" title="No hay reportes en este estado" />
      );
  } else {
    rankingBody = (
      <>
        <RankingTable items={ranking.data.items} offset={ranking.data.offset} />
        <p className="card__note">
          Empates: mayor severidad, luego más confirmaciones, luego el reporte más antiguo.
        </p>
        <Pagination
          offset={ranking.data.offset}
          pageSize={RANKING_PAGE_SIZE}
          total={ranking.data.total}
          onPrevious={() => setPage((current) => Math.max(0, current - 1))}
          onNext={() => setPage((current) => current + 1)}
        />
      </>
    );
  }

  return (
    <div className="page">
      <header className="page__header">
        <div>
          <h1 className="page__title">Priorización de reportes</h1>
          <p className="page__subtitle">{formula(weights.data)}</p>
        </div>
        <div className="page__actions">
          <label htmlFor={filterId} className="visually-hidden">
            Estado
          </label>
          <select
            id={filterId}
            className="select"
            value={filter.key}
            onChange={(event) => changeFilter(event.target.value)}
          >
            {FILTERS.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </header>

      <SummaryCards summary={summary.data} />

      <div className="prioritization">
        <section className="card" aria-labelledby={`${filterId}-map`}>
          <div className="card__header">
            <h2 id={`${filterId}-map`} className="card__title">
              Mapa de calor
            </h2>
            <HeatLegend />
          </div>
          {heat.isError ? (
            <ErrorView
              title="No pudimos cargar el mapa"
              message={problemDetail(heat.error)}
              onRetry={() => void heat.refetch()}
            />
          ) : (
            <>
              <HeatMap points={heat.data ?? []} showReports={showReports} />
              <label className="card__toggle">
                <input
                  type="checkbox"
                  checked={showReports}
                  onChange={(event) => setShowReports(event.target.checked)}
                />
                Ver reportes
              </label>
            </>
          )}
        </section>

        <section className="card" aria-labelledby={`${filterId}-ranking`}>
          <div className="card__header">
            <h2 id={`${filterId}-ranking`} className="card__title">
              Ranking
            </h2>
            <span className="card__hint">Orden: mayor U primero</span>
          </div>
          {rankingBody}
        </section>
      </div>
    </div>
  );
}
