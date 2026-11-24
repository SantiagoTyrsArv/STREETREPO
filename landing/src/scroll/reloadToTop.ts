/** `true` si la página se cargó por una recarga (F5, el botón de recargar o tirar hacia abajo). */
export function isReload(perf: Pick<Performance, "getEntriesByType"> = performance): boolean {
  const [navigation] = perf.getEntriesByType("navigation") as PerformanceNavigationTiming[];
  return navigation?.type === "reload";
}

/**
 * Al recargar, la página vuelve a la portada (fila 134 de la bitácora): el navegador no restaura la
 * posición del *scroll* y se quita el ancla de la URL (p. ej. `#descarga`), que si no lo llevaría
 * a esa sección. Entrar por primera vez con un enlace a una sección sigue llevando a ella.
 */
export function resetScrollOnReload(
  win: Pick<Window, "history" | "location" | "scrollTo"> = window,
  perf: Pick<Performance, "getEntriesByType"> = performance,
  /** Borra la posición que recuerda ScrollTrigger: si no, la restaura al recalcular. */
  forgetScroll: () => void = () => undefined,
): void {
  if ("scrollRestoration" in win.history) {
    win.history.scrollRestoration = "manual";
  }
  if (!isReload(perf)) return;
  forgetScroll();
  if (win.location.hash) {
    win.history.replaceState(null, "", win.location.pathname + win.location.search);
  }
  win.scrollTo(0, 0);
}
