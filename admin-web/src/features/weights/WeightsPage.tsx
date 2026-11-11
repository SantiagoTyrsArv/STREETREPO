import { useId, useState, type ReactNode } from "react";
import { ApiError } from "../../api/client";
import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import {
  useCurrentWeights,
  useReloadWeights,
  useSaveWeights,
  type WeightsInput,
  type WeightVersion,
} from "./api";
import { NormalizationRules } from "./NormalizationRules";
import { VersionsList } from "./VersionsList";
import { WeightsForm } from "./WeightsForm";
import "./weights.css";

const HTTP_NOT_FOUND = 404;
const HTTP_CONFLICT = 409;

function Card({ title, children }: { title: string; children: ReactNode }) {
  const titleId = useId();
  return (
    <section className="card weights-card" aria-labelledby={titleId}>
      <h2 id={titleId} className="card__title">
        {title}
      </h2>
      {children}
    </section>
  );
}

function recalculatedMessage(count: number): string {
  const detail =
    count === 1 ? "Se recalculó 1 reporte activo." : `Se recalcularon ${count} reportes activos.`;
  return `Pesos guardados. ${detail}`;
}

function Editor({ current }: { current: WeightVersion }) {
  const save = useSaveWeights();
  const reload = useReloadWeights();
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  function handleSave(weights: WeightsInput) {
    setSavedMessage(null);
    save.mutate(
      { base_version_id: current.id, ...weights },
      { onSuccess: (saved) => setSavedMessage(recalculatedMessage(saved.recalculated_reports)) },
    );
  }

  const conflict = save.error instanceof ApiError && save.error.status === HTTP_CONFLICT;

  return (
    <>
      {/* La clave reinicia el formulario cuando cambia la versión vigente. */}
      <WeightsForm key={current.id} current={current} saving={save.isPending} onSave={handleSave} />
      {save.isError ? (
        <div className="alert" role="alert">
          <span className="alert__icon" aria-hidden="true">
            !
          </span>
          <div className="weights-alert">
            <p>{save.error.message}</p>
            {conflict ? (
              <button
                type="button"
                className="button button--secondary"
                onClick={() => {
                  save.reset();
                  void reload();
                }}
              >
                Cargar la versión vigente
              </button>
            ) : null}
          </div>
        </div>
      ) : null}
      {savedMessage ? (
        <p className="weights-saved" role="status">
          {savedMessage}
        </p>
      ) : null}
    </>
  );
}

/** Pesos del modelo (HU-14): edición con Σ = 1,00, reglas en solo lectura y versiones. */
export function WeightsPage() {
  const current = useCurrentWeights();

  let editor;
  if (current.isPending) {
    editor = <LoadingView label="Cargando los pesos vigentes…" />;
  } else if (current.isError) {
    const { error } = current;
    editor =
      error instanceof ApiError && error.status === HTTP_NOT_FOUND ? (
        <EmptyView title="Aún no hay pesos configurados" detail={error.message} />
      ) : (
        <ErrorView
          title="No pudimos cargar los pesos"
          message="Hubo un problema al consultar el servidor. Inténtalo de nuevo."
          onRetry={() => void current.refetch()}
        />
      );
  } else {
    editor = <Editor current={current.data} />;
  }

  return (
    <div className="page">
      <header>
        <h1 className="page__title">Pesos del modelo de priorización</h1>
        <p className="page__subtitle weights-intro">
          U = w₁·S + w₂·F + w₃·P. Los pesos deben sumar 1,00. Los valores iniciales son preliminares
          y se ajustan tras la validación con el panel de expertos.
        </p>
      </header>

      <div className="weights-columns">
        <Card title="Ajustar pesos">{editor}</Card>
        <div className="weights-column">
          <Card title="Reglas de normalización (0 a 10)">
            <NormalizationRules />
          </Card>
          <Card title="Versiones de configuración">
            <VersionsList />
          </Card>
        </div>
      </div>
    </div>
  );
}
