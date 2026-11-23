import { useId, useState, type FormEvent } from "react";
import { ApiError } from "../../api/client";
import { useOpenRound } from "./api";

/** Límites del tamaño de muestra por zona (`MAX_SAMPLE_SIZE` de la API). */
export const MIN_SAMPLE_SIZE = 1;
export const MAX_SAMPLE_SIZE = 100;
const DEFAULT_SAMPLE_SIZE = "10";
const NAME_MAX_LENGTH = 100;
const SAMPLE_SIZE_MESSAGE = `El tamaño de la muestra debe ser un número entero de ${MIN_SAMPLE_SIZE} a ${MAX_SAMPLE_SIZE}.`;
const UNKNOWN_PROBLEM = "No pudimos abrir la ronda. Inténtalo de nuevo.";

function parseSampleSize(value: string): number | null {
  if (!/^\d+$/.test(value.trim())) {
    return null;
  }
  const size = Number(value);
  return size >= MIN_SAMPLE_SIZE && size <= MAX_SAMPLE_SIZE ? size : null;
}

/** Los mensajes del servidor ya dicen qué pasó (otra ronda abierta, zona con pocos reportes…). */
function problemMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : UNKNOWN_PROBLEM;
}

/** «Abrir ronda»: congela la muestra de reportes de cada zona (ADR 0008). */
export function OpenRoundForm() {
  const nameId = useId();
  const sizeId = useId();
  const hintId = useId();
  const [name, setName] = useState("");
  const [sampleSize, setSampleSize] = useState(DEFAULT_SAMPLE_SIZE);
  const [problem, setProblem] = useState<string | null>(null);
  const openRound = useOpenRound();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (openRound.isPending) {
      return;
    }
    const size = parseSampleSize(sampleSize);
    if (size === null) {
      setProblem(SAMPLE_SIZE_MESSAGE);
      return;
    }
    setProblem(null);
    openRound.mutate(
      { name: name.trim(), sample_size: size },
      {
        onSuccess: () => setName(""),
        onError: (error) => setProblem(problemMessage(error)),
      },
    );
  }

  return (
    <form className="card open-round" onSubmit={handleSubmit} aria-labelledby={`${nameId}-title`}>
      <div className="card__header">
        <h2 className="card__title validation-title" id={`${nameId}-title`}>
          Abrir una ronda de evaluación
        </h2>
      </div>
      <div className="open-round__body">
        <p className="open-round__intro">
          Se toma una muestra de los reportes activos de cada zona con su urgencia U y el orden del
          motor. Los evaluadores la ordenan a ciegas.
        </p>
        {problem ? (
          <div className="alert" role="alert">
            <span className="alert__icon" aria-hidden="true">
              !
            </span>
            <p>{problem}</p>
          </div>
        ) : null}
        <div className="open-round__fields">
          <div className="field">
            <label htmlFor={nameId}>Nombre de la ronda</label>
            <input
              id={nameId}
              required
              maxLength={NAME_MAX_LENGTH}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor={sizeId}>Reportes por zona (muestra)</label>
            <input
              id={sizeId}
              inputMode="numeric"
              aria-describedby={hintId}
              required
              value={sampleSize}
              onChange={(event) => setSampleSize(event.target.value)}
            />
            <p id={hintId} className="field__hint">
              De {MIN_SAMPLE_SIZE} a {MAX_SAMPLE_SIZE}. Una zona con menos reportes entra con todos
              los que tiene.
            </p>
          </div>
        </div>
        <div>
          <button type="submit" className="button" disabled={openRound.isPending}>
            {openRound.isPending ? "Abriendo…" : "Abrir ronda"}
          </button>
        </div>
      </div>
    </form>
  );
}
