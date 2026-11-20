import { vi } from "vitest";

/** IntersectionObserver simulado: `set(true|false)` avisa a todos los observadores. */
export function mockIntersection() {
  const observers = new Set<{ cb: IntersectionObserverCallback; targets: Element[] }>();
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      private entry: { cb: IntersectionObserverCallback; targets: Element[] };
      constructor(cb: IntersectionObserverCallback) {
        this.entry = { cb, targets: [] };
        observers.add(this.entry);
      }
      observe(el: Element) {
        this.entry.targets.push(el);
      }
      unobserve() {}
      disconnect() {
        observers.delete(this.entry);
      }
    },
  );
  return {
    set(isIntersecting: boolean) {
      for (const { cb, targets } of observers) {
        cb(
          targets.map((target) => ({ target, isIntersecting }) as IntersectionObserverEntry),
          {} as IntersectionObserver,
        );
      }
    },
    get count() {
      return observers.size;
    },
  };
}
