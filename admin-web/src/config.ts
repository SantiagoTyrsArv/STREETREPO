/** Configuración del panel, leída de las variables `VITE_*` al compilar. */
export const DEFAULT_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export type AppConfig = {
  /** Origen de la API, sin barra final. */
  readonly apiBaseUrl: string;
  /** Plantilla de teselas del mapa (guía 3.1). */
  readonly tileUrl: string;
};

type Env = { readonly VITE_API_BASE_URL?: string; readonly VITE_TILE_URL?: string };

export function readConfig(env: Env): AppConfig {
  const apiBaseUrl = env.VITE_API_BASE_URL?.trim();
  if (!apiBaseUrl) {
    throw new Error("Falta VITE_API_BASE_URL: define el origen de la API (ver .env.example).");
  }
  return {
    apiBaseUrl: apiBaseUrl.replace(/\/+$/, ""),
    tileUrl: env.VITE_TILE_URL?.trim() || DEFAULT_TILE_URL,
  };
}

export const config: AppConfig = readConfig(import.meta.env);
