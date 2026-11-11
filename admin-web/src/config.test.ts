import { describe, expect, it } from "vitest";
import { DEFAULT_TILE_URL, readConfig } from "./config";

describe("readConfig", () => {
  it("exige la URL de la API", () => {
    expect(() => readConfig({})).toThrow("VITE_API_BASE_URL");
  });

  it("quita la barra final de la URL de la API", () => {
    expect(readConfig({ VITE_API_BASE_URL: "http://localhost:8000/" }).apiBaseUrl).toBe(
      "http://localhost:8000",
    );
  });

  it("usa las teselas públicas de OpenStreetMap por defecto", () => {
    expect(readConfig({ VITE_API_BASE_URL: "http://a" }).tileUrl).toBe(DEFAULT_TILE_URL);
  });

  it("respeta el proveedor de teselas configurado", () => {
    const config = readConfig({ VITE_API_BASE_URL: "http://a", VITE_TILE_URL: "http://t/{z}" });
    expect(config.tileUrl).toBe("http://t/{z}");
  });
});
