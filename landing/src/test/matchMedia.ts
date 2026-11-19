import { vi } from "vitest";

/** Simula `matchMedia` con un valor de `prefers-reduced-motion` que se puede cambiar. */
export function mockReducedMotion(initial: boolean) {
  let matches = initial;
  const listeners = new Set<(event: MediaQueryListEvent) => void>();
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      get matches() {
        return query.includes("prefers-reduced-motion") ? matches : false;
      },
      media: query,
      addEventListener: (_: string, cb: (event: MediaQueryListEvent) => void) => listeners.add(cb),
      removeEventListener: (_: string, cb: (event: MediaQueryListEvent) => void) =>
        listeners.delete(cb),
    })),
  );
  return {
    set(value: boolean) {
      matches = value;
      listeners.forEach((cb) => cb({ matches: value } as MediaQueryListEvent));
    },
  };
}
