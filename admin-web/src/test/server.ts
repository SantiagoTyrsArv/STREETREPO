import { HttpResponse } from "msw";
import { setupServer } from "msw/node";

/** Origen de la API en las pruebas (`VITE_API_BASE_URL` en `vite.config.ts`). */
export const API = "http://api.test";

/** Servidor simulado; cada prueba registra sus rutas con `server.use(...)`. */
export const server = setupServer();

/** Respuesta de error con el formato uniforme de la API (guía 6.1). */
export function apiError(
  status: number,
  code: string,
  message: string,
  details: Record<string, unknown> = {},
) {
  return HttpResponse.json({ code, message, details }, { status });
}
