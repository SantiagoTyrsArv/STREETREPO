import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SEQUENCE_COPY } from "../content/copy";
import { mockReducedMotion } from "../test/matchMedia";
import { SEQUENCE_CHAPTERS, SequenceChapter } from "./SequenceChapter";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SequenceChapter con movimiento reducido", () => {
  it.each(SEQUENCE_CHAPTERS.map((c) => [c.id, c] as const))(
    "%s muestra su cuadro clave fijo y su texto completo",
    (_id, chapter) => {
      mockReducedMotion(true);
      vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
      const copy = SEQUENCE_COPY[chapter.id];

      const { container } = render(<SequenceChapter chapter={chapter} />);

      const still = screen.getByRole("img", { name: copy.alt });
      expect(still).toHaveAttribute("src", `/media/${chapter.id}/key.webp`);
      expect(container.querySelector("canvas")).toBeNull();
      expect(screen.getByRole("heading", { name: copy.title })).toBeInTheDocument();
      expect(screen.getByText(copy.lead)).toBeInTheDocument();
    },
  );
});
