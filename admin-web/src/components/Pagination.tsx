type Props = {
  /** Posición del primer elemento visible, desde 0. */
  offset: number;
  pageSize: number;
  total: number;
  onPrevious: () => void;
  onNext: () => void;
};

/** Paginación de los listados: «21–40 de 45» con Anterior y Siguiente. */
export function Pagination({ offset, pageSize, total, onPrevious, onNext }: Props) {
  const first = offset + 1;
  const last = Math.min(offset + pageSize, total);
  return (
    <nav className="pagination" aria-label="Paginación">
      <span aria-live="polite">
        {first}–{last} de {total}
      </span>
      <button
        type="button"
        className="button button--secondary"
        onClick={onPrevious}
        disabled={offset === 0}
      >
        Anterior
      </button>
      <button
        type="button"
        className="button button--secondary"
        onClick={onNext}
        disabled={last >= total}
      >
        Siguiente
      </button>
    </nav>
  );
}
