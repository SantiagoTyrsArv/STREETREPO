import { afterEach, describe, expect, it, vi } from "vitest";
import { measureCenters } from "./measure";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("measureCenters", () => {
  it("mide cada parte en su sitio final, sin el desplazamiento del revelado, y lo devuelve", () => {
    const root = document.createElement("h2");
    const line = document.createElement("div");
    line.className = "reveal__line";
    line.style.transform = "translateY(110%) rotate(4deg)";
    const word = document.createElement("span");
    word.style.transform = "translateY(110%)";
    line.append(word);
    root.append(line);
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (
      this: HTMLElement,
    ) {
      if (this === root) return new DOMRect(0, 0, 400, 100);
      // Si el revelado sigue aplicado, la palabra aparece 50 px más abajo.
      const shifted = line.style.transform !== "none" || word.style.transform !== "none";
      return new DOMRect(10, shifted ? 60 : 10, 40, 20);
    });

    const centers = measureCenters(root, [word]);
    expect(centers).toEqual([{ x: 30, y: 20 }]);
    expect(line.style.transform).toBe("translateY(110%) rotate(4deg)");
    expect(word.style.transform).toBe("translateY(110%)");
  });
});
