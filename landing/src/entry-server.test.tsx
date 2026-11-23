// @vitest-environment node
import { describe, expect, it } from "vitest";
import { COPY } from "./content/copy";
import { render } from "./entry-server";

describe("render", () => {
  it("renderiza sin navegador", () => {
    expect(() => render()).not.toThrow();
  });

  it("incluye la portada y todos los capítulos", () => {
    const html = render();
    expect(html).toContain("STREET");
    expect(html).toContain("EPO");
    const titles = [
      COPY.apertura.title,
      COPY.problema.title,
      COPY.reportar.title,
      COPY.priorizar.title,
      COPY.calculadora.title,
      COPY.panel.title,
      COPY.reparado.title,
      COPY.descarga.title,
    ];
    for (const title of titles) {
      expect(html).toContain(escape(title));
    }
  });
});

/** El HTML del servidor escapa comillas y apóstrofos. */
function escape(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
}
