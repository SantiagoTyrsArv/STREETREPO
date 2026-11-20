import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { PromoVideo } from "../config/video";
import * as smooth from "../scroll/useSmoothScroll";
import { VideoButton } from "./VideoButton";
import { VideoSection } from "./VideoSection";

const VIDEO: PromoVideo = {
  youtubeId: "abc123XYZ_0",
  title: "Street Repo en 60 segundos",
  poster: "/media/video/poster.webp",
  aiGenerated: true,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("video promocional", () => {
  it("sin video configurado no aparece nada", () => {
    const { container } = render(
      <>
        <VideoButton video={null} />
        <VideoSection video={null} />
      </>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("la sección muestra el título y la etiqueta de IA, y YouTube no carga hasta reproducir", () => {
    const { container } = render(<VideoSection video={VIDEO} />);
    expect(container.querySelector("section")).toHaveAttribute("id", "video");
    expect(screen.getByText("Recreación generada con IA")).toBeInTheDocument();
    expect(container.ownerDocument.querySelector("iframe")).toBeNull();
  });

  it("reproducir abre el reproductor sin cookies; Esc lo cierra y el foco vuelve", () => {
    const pause = vi.spyOn(smooth, "pauseSmoothScroll");
    const resume = vi.spyOn(smooth, "resumeSmoothScroll");
    render(<VideoSection video={VIDEO} />);
    const play = screen.getByRole("button", { name: /reproducir/i });
    play.focus();
    fireEvent.click(play);

    const iframe = document.querySelector("iframe");
    expect(iframe?.getAttribute("src")).toMatch(
      /^https:\/\/www\.youtube-nocookie\.com\/embed\/abc123XYZ_0\?autoplay=1/,
    );
    expect(iframe).toHaveAttribute("title", VIDEO.title);
    expect(pause).toHaveBeenCalled();

    const dialog = document.querySelector("dialog") as HTMLDialogElement;
    act(() => {
      dialog.dispatchEvent(new Event("cancel", { cancelable: true }));
      dialog.close();
    });
    expect(document.querySelector("iframe")).toBeNull();
    expect(resume).toHaveBeenCalled();
    expect(document.activeElement).toBe(play);
  });

  it("el botón de la portada abre el mismo reproductor", () => {
    render(<VideoButton video={VIDEO} />);
    fireEvent.click(screen.getByRole("button", { name: "Ver el video" }));
    expect(document.querySelector("iframe")).not.toBeNull();
  });
});
