/** Reglas de la guía 2.2, tal como las aplica el servidor. Aquí solo se leen. */
const RULES: ReadonlyArray<{ factor: string; text: string }> = [
  { factor: "S Severidad", text: "Baja = 3 · Media = 6 · Alta = 10" },
  {
    factor: "F Flujo",
    text: "Por jerarquía vial OSM: primaria 10 · secundaria 7 · terciaria 5 · residencial, sin clasificar o de servicio 2. Sin vía asociada: 2 y se marca “Revisar vía”.",
  },
  {
    factor: "P Proximidad",
    text: "10 si el servicio crítico está a 100 m o menos; decrece linealmente hasta 0 a 500 m.",
  },
];

export function NormalizationRules() {
  return (
    <>
      <dl className="rules">
        {RULES.map(({ factor, text }) => (
          <div key={factor} className="rules__row">
            <dt>{factor}</dt>
            <dd>{text}</dd>
          </div>
        ))}
      </dl>
      <p className="card__hint">
        Solo lectura. Los cambios de reglas se hacen con validación de expertos.
      </p>
    </>
  );
}
