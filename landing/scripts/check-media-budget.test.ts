import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { BUDGET, checkBudget, measure } from "./check-media-budget";

describe("checkBudget", () => {
  it("no informa nada si todo está dentro del presupuesto", () => {
    expect(checkBudget({ initialBytes: 6e6, desktopBytes: 45e6, mobileBytes: 25e6 })).toEqual([]);
  });

  it("nombra la parte que se pasa y su límite", () => {
    const problems = checkBudget({ initialBytes: 1e6, desktopBytes: 46e6, mobileBytes: 1e6 });
    expect(problems).toHaveLength(1);
    expect(problems[0]).toContain("escritorio");
    expect(problems[0]).toContain("45 MB");
  });

  it("informa cada incumplimiento por separado", () => {
    const problems = checkBudget({ initialBytes: 7e6, desktopBytes: 1e6, mobileBytes: 26e6 });
    expect(problems).toHaveLength(2);
    expect(problems[0]).toContain("inicial");
    expect(problems[1]).toContain("móvil");
  });

  it("usa los límites del diseño (6, 45 y 25 MB)", () => {
    expect(BUDGET).toEqual({ initialBytes: 6e6, desktopBytes: 45e6, mobileBytes: 25e6 });
  });
});

describe("measure", () => {
  let root: string;

  afterEach(() => rmSync(root, { recursive: true, force: true }));

  function file(path: string, bytes: number) {
    const full = join(root, path);
    mkdirSync(join(full, ".."), { recursive: true });
    writeFileSync(full, Buffer.alloc(bytes));
  }

  it("separa escritorio y móvil, y suma la portada, las fuentes y el ícono al inicial", () => {
    root = mkdtempSync(join(tmpdir(), "budget-"));
    file("public/favicon.svg", 1);
    file("public/media/apertura/key.webp", 10);
    file("public/media/apertura/manifest.json", 2);
    file("public/media/apertura/desktop/frame_0001.webp", 100);
    file("public/media/apertura/mobile/frame_0001.webp", 300);
    file("public/media/problema/desktop/frame_0001.webp", 1000);
    file("public/media/problema/mobile/frame_0001.webp", 2000);
    file("public/media/panel/panel.webp", 5);
    file("dist/assets/manrope.woff2", 20);
    file("dist/assets/index.js", 999);

    expect(measure(root)).toEqual({
      // Comunes: key 10 + manifest 2 + panel 5 = 17.
      desktopBytes: 17 + 100 + 1000,
      mobileBytes: 17 + 300 + 2000,
      // El mayor de los dos: portada móvil 300 + key 10 + manifest 2 + fuente 20 + ícono 1.
      initialBytes: 300 + 10 + 2 + 20 + 1,
    });
  });
});
