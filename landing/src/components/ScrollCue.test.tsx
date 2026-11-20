import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ScrollCue } from "./ScrollCue";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ScrollCue", () => {
  it("invita a deslizar y se va para siempre al empezar el scroll", () => {
    render(<ScrollCue />);
    expect(screen.getByText("Desliza")).toBeInTheDocument();

    act(() => {
      vi.stubGlobal("scrollY", 100);
      window.dispatchEvent(new Event("scroll"));
    });
    expect(screen.queryByText("Desliza")).toBeNull();

    act(() => {
      vi.stubGlobal("scrollY", 0);
      window.dispatchEvent(new Event("scroll"));
    });
    expect(screen.queryByText("Desliza")).toBeNull();
  });
});
