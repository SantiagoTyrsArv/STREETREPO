/**
 * Sigue si un elemento está en pantalla (con un margen), para que las animaciones de cada cuadro
 * no trabajen fuera de la vista. Sin IntersectionObserver se considera siempre visible.
 */
export function trackVisibility(
  el: Element,
  rootMargin = "10% 0px",
): { readonly visible: boolean; stop(): void } {
  const state = { visible: true, stop: () => undefined as void };
  if (typeof IntersectionObserver !== "function") {
    return state;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        state.visible = entry.isIntersecting;
      }
    },
    { rootMargin },
  );
  observer.observe(el);
  state.stop = () => observer.disconnect();
  return state;
}
