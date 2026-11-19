import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Release } from "../config/release";
import { DownloadSection } from "./DownloadSection";

const release: Release = {
  version: "1.0.0",
  apkUrl: "https://example.invalid/street-repo-1.0.0.apk",
  sizeBytes: 25_480_000,
  sha256: "a".repeat(64),
  minAndroid: "8.0",
};

describe("DownloadSection sin versión publicada", () => {
  it("anuncia «Próximamente» y no ofrece ningún .apk", () => {
    const { container } = render(<DownloadSection release={null} />);

    const section = container.querySelector("#descarga");
    expect(section).toHaveAttribute("tabindex", "-1");
    expect(screen.getByText("Próximamente")).toBeInTheDocument();
    expect(screen.getByText(/en pruebas/i)).toBeInTheDocument();
    expect(container.querySelector('a[href$=".apk"]')).toBeNull();
  });
});

describe("DownloadSection con una versión publicada", () => {
  it("enlaza el APK con versión, tamaño, requisito y suma SHA-256", () => {
    render(<DownloadSection release={release} />);

    const link = screen.getByRole("link", { name: "Descargar Street Repo para Android" });
    expect(link).toHaveAttribute("href", release.apkUrl);
    expect(screen.getByText(/1\.0\.0/)).toBeInTheDocument();
    expect(screen.getByText(/24,3 MB/)).toBeInTheDocument();
    expect(screen.getByText(/Android 8\.0 o superior/)).toBeInTheDocument();
    const code = screen.getByText(release.sha256);
    expect(code.tagName).toBe("CODE");
    expect(screen.queryByText("Próximamente")).toBeNull();
  });

  it("muestra un QR hacia el APK con texto alternativo", () => {
    render(<DownloadSection release={release} />);

    const qr = screen.getByRole("img", { name: /código QR/i });
    expect(qr.querySelector("path")?.getAttribute("d")).toMatch(/^M\d/);
  });

  it("explica los pasos de instalación en orden", () => {
    render(<DownloadSection release={release} />);

    const steps = within(screen.getByRole("list", { name: /pasos/i })).getAllByRole("listitem");
    expect(steps).toHaveLength(3);
    expect(steps[0]).toHaveTextContent(/apps desconocidas/i);
    expect(steps[1]).toHaveTextContent(/abre el archivo/i);
    expect(steps[2]).toHaveTextContent(/instalar/i);
  });
});
