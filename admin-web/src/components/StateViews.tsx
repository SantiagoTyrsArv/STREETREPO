/** Estados de pantalla compartidos (guía 10.3): cargando, vacío y error con reintento. */

export function LoadingView({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="state-view" role="status">
      {label}
    </div>
  );
}

type EmptyProps = {
  title: string;
  detail?: string;
  /** Signo grande sobre el título (Figma «Sin reportes»: un «0»). */
  mark?: string;
};

export function EmptyView({ title, detail, mark }: EmptyProps) {
  return (
    <div className="state-view">
      {mark ? (
        <span className="state-view__mark" aria-hidden="true">
          {mark}
        </span>
      ) : null}
      <p className="state-view__title">{title}</p>
      {detail ? <p>{detail}</p> : null}
    </div>
  );
}

type ErrorProps = {
  /** Qué no se pudo hacer (Figma «Error al cargar»). */
  title?: string;
  message: string;
  onRetry: () => void;
};

export function ErrorView({ title, message, onRetry }: ErrorProps) {
  return (
    <div className="state-view state-view--error" role="alert">
      {title ? (
        <>
          <span className="state-view__mark" aria-hidden="true">
            !
          </span>
          <p className="state-view__title">{title}</p>
        </>
      ) : null}
      <p className="state-view__message">{message}</p>
      <button type="button" className="button" onClick={onRetry}>
        Reintentar
      </button>
    </div>
  );
}
