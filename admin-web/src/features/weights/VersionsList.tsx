import { useState } from "react";
import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import { formatDateTime, formatScore } from "../../format/format";
import { useWeightVersions, VERSIONS_PAGE_SIZE } from "./api";

/** Sin autor, la versión es la que cargó el sistema al instalarse. */
const INITIAL_CONFIGURATION = "Configuración inicial";

/** Versiones de configuración, de la más nueva a la más antigua; ninguna se edita. */
export function VersionsList() {
  const [page, setPage] = useState(0);
  const versions = useWeightVersions(page);

  if (versions.isPending) {
    return <LoadingView label="Cargando las versiones…" />;
  }
  if (versions.isError) {
    return (
      <ErrorView
        message="No pudimos cargar las versiones. Inténtalo de nuevo."
        onRetry={() => void versions.refetch()}
      />
    );
  }
  const { items } = versions.data;
  // La API no informa el total: hay más si la página llegó completa.
  const hasNext = items.length === VERSIONS_PAGE_SIZE;

  return (
    <>
      {items.length === 0 ? (
        <EmptyView title="No hay más versiones" />
      ) : (
        <ul className="versions">
          {items.map((version) => (
            <li key={version.id} className="versions__item">
              <div>
                <p className="versions__weights">
                  {formatScore(version.w_severity)} / {formatScore(version.w_flow)} /{" "}
                  {formatScore(version.w_proximity)}
                </p>
                <p className="versions__meta">
                  {formatDateTime(version.created_at)} ·{" "}
                  {version.created_by_name ?? INITIAL_CONFIGURATION}
                </p>
              </div>
              {version.is_current ? (
                <span className="chip" data-status="reparado">
                  Vigente
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      {page > 0 || hasNext ? (
        <nav className="pagination" aria-label="Paginación de versiones">
          <button
            type="button"
            className="button button--secondary"
            onClick={() => setPage((current) => Math.max(0, current - 1))}
            disabled={page === 0}
          >
            Más recientes
          </button>
          <button
            type="button"
            className="button button--secondary"
            onClick={() => setPage((current) => current + 1)}
            disabled={!hasNext}
          >
            Más antiguas
          </button>
        </nav>
      ) : null}
    </>
  );
}
