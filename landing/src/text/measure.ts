/**
 * Centros de `parts` respecto a `root`, medidos en su sitio final: se quitan un instante los
 * `transform` del revelado (de cada parte y de sus contenedores hasta `root`) y se restauran en el
 * mismo cuadro, sin que llegue a pintarse. Así el *warp* y la proximidad reaccionan donde están
 * las palabras cuando ya entraron, no una línea más abajo.
 */
export function measureCenters(
  root: HTMLElement,
  parts: readonly HTMLElement[],
): { x: number; y: number }[] {
  const touched = new Map<HTMLElement, string>();
  for (const part of parts) {
    let el: HTMLElement | null = part;
    while (el && el !== root) {
      if (!touched.has(el)) {
        touched.set(el, el.style.transform);
        el.style.transform = "none";
      }
      el = el.parentElement;
    }
  }
  const box = root.getBoundingClientRect();
  const centers = parts.map((part) => {
    const r = part.getBoundingClientRect();
    return { x: r.left + r.width / 2 - box.left, y: r.top + r.height / 2 - box.top };
  });
  touched.forEach((transform, el) => {
    el.style.transform = transform;
  });
  return centers;
}
