import { describe, expect, it, vi } from "vitest";
import { isReload, resetScrollOnReload } from "./reloadToTop";

function perf(type: string | null) {
  return { getEntriesByType: () => (type ? [{ type }] : []) } as unknown as Performance;
}

function fakeWindow(hash = "") {
  return {
    history: { scrollRestoration: "auto", replaceState: vi.fn() },
    location: { hash, pathname: "/", search: "?a=1" },
    scrollTo: vi.fn(),
  } as unknown as Window;
}

describe("isReload", () => {
  it("distingue la recarga de la primera visita", () => {
    expect(isReload(perf("reload"))).toBe(true);
    expect(isReload(perf("navigate"))).toBe(false);
    expect(isReload(perf(null))).toBe(false);
  });
});

describe("resetScrollOnReload", () => {
  it("al recargar vuelve a la portada y quita el ancla", () => {
    const win = fakeWindow("#descarga");
    const forget = vi.fn();
    resetScrollOnReload(win, perf("reload"), forget);
    expect(forget).toHaveBeenCalledOnce();
    expect(win.history.scrollRestoration).toBe("manual");
    expect(win.history.replaceState).toHaveBeenCalledWith(null, "", "/?a=1");
    expect(win.scrollTo).toHaveBeenCalledWith(0, 0);
  });

  it("en la primera visita respeta el enlace a una sección", () => {
    const win = fakeWindow("#descarga");
    const forget = vi.fn();
    resetScrollOnReload(win, perf("navigate"), forget);
    expect(forget).not.toHaveBeenCalled();
    expect(win.history.scrollRestoration).toBe("manual");
    expect(win.history.replaceState).not.toHaveBeenCalled();
    expect(win.scrollTo).not.toHaveBeenCalled();
  });
});
