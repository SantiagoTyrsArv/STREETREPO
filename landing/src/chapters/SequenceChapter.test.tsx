import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SCENE_DURATION_MS, SEQUENCE_CHAPTERS, SequenceChapter } from "./SequenceChapter";

vi.mock("../scroll/useChapterPlayback", () => ({
  useChapterPlayback: () => ({ progress: 1, near: true }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SEQUENCE_CHAPTERS", () => {
  it("las escenas se reproducen a su velocidad real (129 cuadros a 16 fps)", () => {
    expect(SCENE_DURATION_MS).toBeGreaterThanOrEqual((129 / 16) * 1000 - 100);
    expect(SEQUENCE_CHAPTERS.every((c) => c.durationMs === SCENE_DURATION_MS)).toBe(true);
  });

  it("solo la portada sigue al scroll; ninguna se reproduce al cargar", () => {
    expect(SEQUENCE_CHAPTERS.filter((c) => c.scrub).map((c) => c.id)).toEqual(["apertura"]);
  });
});

describe("SequenceChapter al terminar su reproducción", () => {
  it.each(SEQUENCE_CHAPTERS.filter((c) => c.id !== "apertura").map((c) => [c.id, c] as const))(
    "%s deja el texto visible",
    (_id, chapter) => {
      vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
      const { container } = render(<SequenceChapter chapter={chapter} />);
      const content = container.querySelector<HTMLElement>(".chapter__content");
      expect(content?.style.opacity === "" || Number(content?.style.opacity) === 1).toBe(true);
      const scene = container.querySelector<HTMLElement>(".chapter__scene");
      expect(scene?.style.filter ?? "").not.toMatch(/blur\([1-9]/);
    },
  );
});
