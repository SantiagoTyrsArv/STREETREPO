/**
 * Enlaces internos (`#descarga`) con desplazamiento suave activo.
 *
 * Lenis guarda su propia posición: si el navegador salta al ancla por su cuenta, Lenis devuelve la
 * página a donde estaba. Por eso el salto se delega en `scrollTo` (Lenis) y el foco se mueve a mano,
 * para que el enlace «Saltar a la descarga» sirva de verdad a quien navega con teclado.
 */
export function bindAnchorNavigation(
  root: Document,
  scrollTo: (target: HTMLElement) => void,
): () => void {
  const onClick = (event: MouseEvent): void => {
    if (event.defaultPrevented || event.button !== 0) {
      return;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    const link = (event.target as Element | null)?.closest?.("a[href^='#']");
    const id = link?.getAttribute("href")?.slice(1);
    const target = id ? root.getElementById(decodeURIComponent(id)) : null;
    if (!target) {
      return;
    }
    event.preventDefault();
    scrollTo(target);
    target.focus({ preventScroll: true });
    history.pushState(null, "", `#${id}`);
  };
  root.addEventListener("click", onClick);
  return () => root.removeEventListener("click", onClick);
}
