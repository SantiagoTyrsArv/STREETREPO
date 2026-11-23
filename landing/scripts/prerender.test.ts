import { describe, expect, it } from "vitest";
import { injectApp } from "./prerender";

describe("injectApp", () => {
  it("inyecta la app en el contenedor", () => {
    expect(injectApp('<body><div id="root"></div></body>', "<main>x</main>")).toBe(
      '<body><div id="root"><main>x</main></div></body>',
    );
  });

  it("falla si no hay contenedor vacío", () => {
    expect(() => injectApp("<body></body>", "<main>x</main>")).toThrow(
      'Falta <div id="root"></div> en index.html',
    );
  });
});
