import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SEQUENCE_CHAPTERS, SequenceChapter } from "./SequenceChapter";

vi.mock("../scroll/useChapterPlayback", () => ({
  useChapterPlayback: () => ({ progress: 1, near: true }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SEQUENCE_CHAPTERS", () => {
  it("los capítulos de escena duran lo del diseño", () => {
    expect(SEQUENCE_CHAPTERS.map((c) => [c.id, c.durationMs])).toEqual([
      ["apertura", 4500],
      ["problema", 3000],
      ["priorizar", 3500],
      ["reparado", 3000],
    ]);
  });

  it("solo la apertura se reproduce al cargar", () => {
    expect(SEQUENCE_CHAPTERS.filter((c) => c.autoplay).map((c) => c.id)).toEqual(["apertura"]);
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
