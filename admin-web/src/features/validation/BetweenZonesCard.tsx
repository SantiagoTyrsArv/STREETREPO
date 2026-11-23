import { useId } from "react";
import type { RoundResults } from "./api";
import { formatCoefficient, formatPValue } from "./resultsFormat";

/** α de la prueba entre zonas (`SIGNIFICANCE_ALPHA` de la API). */
const ALPHA_LABEL = "0,05";

export const TEST_LABELS: Record<string, string> = {
  mann_whitney: "U de Mann-Whitney",
  kruskal_wallis: "H de Kruskal-Wallis",
};

/** Prueba entre zonas sobre el desacuerdo motor-panel; si no se calculó, dice por qué. */
export function BetweenZonesCard({ between }: { between: RoundResults["between"] }) {
  const titleId = useId();
  return (
    <section className="card result-card" aria-labelledby={titleId}>
      <h3 className="validation-title result-card__title" id={titleId}>
        Prueba entre zonas
      </h3>
      {between.computable &&
      typeof between.statistic === "number" &&
      typeof between.p_value === "number" ? (
        <>
          <dl className="metrics">
            <dt>Prueba</dt>
            <dd>{TEST_LABELS[between.test ?? ""] ?? between.test}</dd>
            <dt>Estadístico</dt>
            <dd>{formatCoefficient(between.statistic)}</dd>
            <dt>Valor p</dt>
            <dd>{formatPValue(between.p_value)}</dd>
          </dl>
          <p className="result-verdict">
            Diferencia significativa con α = {ALPHA_LABEL}: {between.significant ? "Sí" : "No"}
          </p>
        </>
      ) : (
        <p>No se calculó: {between.reason}</p>
      )}
      <p className="card__hint">
        Compara el desacuerdo |motor − panel| / (n − 1) de cada reporte entre las zonas de alta y
        baja concentración.
      </p>
    </section>
  );
}
