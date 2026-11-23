import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { draftKey, useDraftOrder } from "./useDraftOrder";

const IDS = ["a", "b", "c"];

beforeEach(() => sessionStorage.clear());

describe("borrador del orden", () => {
  it("empieza con el orden del servidor", () => {
    const { result } = renderHook(() => useDraftOrder("r-1", 1, IDS));

    expect(result.current.ids).toEqual(IDS);
  });

  it("subir, bajar y mover cambian el orden sin salirse de la lista", () => {
    const { result } = renderHook(() => useDraftOrder("r-1", 1, IDS));

    act(() => result.current.moveUp("b"));
    expect(result.current.ids).toEqual(["b", "a", "c"]);
    act(() => result.current.moveUp("b"));
    expect(result.current.ids).toEqual(["b", "a", "c"]);
    act(() => result.current.moveDown("a"));
    expect(result.current.ids).toEqual(["b", "c", "a"]);
    act(() => result.current.moveDown("a"));
    expect(result.current.ids).toEqual(["b", "c", "a"]);
    act(() => result.current.move(2, 0));
    expect(result.current.ids).toEqual(["a", "b", "c"]);
  });

  it("recargar conserva el borrador de esa ronda y zona", () => {
    const first = renderHook(() => useDraftOrder("r-1", 1, IDS));
    act(() => first.result.current.moveDown("a"));
    first.unmount();

    const again = renderHook(() => useDraftOrder("r-1", 1, IDS));
    const otherZone = renderHook(() => useDraftOrder("r-1", 2, IDS));

    expect(again.result.current.ids).toEqual(["b", "a", "c"]);
    expect(otherZone.result.current.ids).toEqual(IDS);
  });

  it("descarta un borrador que no tiene los mismos reportes", () => {
    sessionStorage.setItem(draftKey("r-1", 1), JSON.stringify(["c", "x", "a"]));

    const { result } = renderHook(() => useDraftOrder("r-1", 1, IDS));

    expect(result.current.ids).toEqual(IDS);
  });

  it("descarta un borrador ilegible", () => {
    sessionStorage.setItem(draftKey("r-1", 1), "{no es json");

    const { result } = renderHook(() => useDraftOrder("r-1", 1, IDS));

    expect(result.current.ids).toEqual(IDS);
  });

  it("reset vuelve al orden del servidor y borra el borrador", () => {
    const { result } = renderHook(() => useDraftOrder("r-1", 1, IDS));
    act(() => result.current.moveDown("a"));

    act(() => result.current.reset());

    expect(result.current.ids).toEqual(IDS);
    expect(sessionStorage.getItem(draftKey("r-1", 1))).toBeNull();
  });
});
