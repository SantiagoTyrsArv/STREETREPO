/** Estados de pantalla compartidos (guía 10.3): cargando, vacío y error con reintento. */

export function LoadingView({ label = "Cargando…" }: { label?: string }) {
  return (
    <div className="state-view" role="status">
      {label}
    </div>
  );
}

export function EmptyView({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="state-view">
      <p className="state-view__title">{title}</p>
      {detail ? <p>{detail}</p> : null}
    </div>
  );
}

export function ErrorView({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="state-view state-view--error" role="alert">
      <p className="state-view__message">{message}</p>
      <button type="button" className="button button--secondary" onClick={onRetry}>
        Reintentar
      </button>
    </div>
  );
}
