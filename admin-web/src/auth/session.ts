/**
 * Sesión web del panel (decisión 42, ADR 0004): el acceso llega en el cuerpo y vive en memoria;
 * el refresco viaja en la cookie `sr_refresh` (`HttpOnly`), que este código nunca lee.
 */
import { fetchOrNetworkError, toApiError } from "../api/client";
import type { components } from "../api/schema";
import { config } from "../config";

type WebTokenResponse = components["schemas"]["WebTokenResponse"];

export type WebTokens = { accessToken: string; expiresIn: number };

const WEB_AUTH_PATH = "/api/v1/auth/web";
/** Cabecera anti-CSRF que exigen las rutas de sesión web. */
const CSRF_HEADER = "X-CSRF-Protection";
const HTTP_UNAUTHORIZED = 401;
const HTTP_FORBIDDEN = 403;

function post(action: "login" | "refresh" | "logout", body?: unknown): Promise<Response> {
  const headers = new Headers({ [CSRF_HEADER]: "1" });
  if (body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  return fetchOrNetworkError(`${config.apiBaseUrl}${WEB_AUTH_PATH}/${action}`, {
    method: "POST",
    credentials: "include",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function toTokens(response: Response): Promise<WebTokens> {
  const body = (await response.json()) as WebTokenResponse;
  return { accessToken: body.access_token, expiresIn: body.expires_in };
}

export async function webLogin(email: string, password: string): Promise<WebTokens> {
  const response = await post("login", { email, password });
  if (!response.ok) {
    throw await toApiError(response);
  }
  return toTokens(response);
}

/**
 * Renueva el acceso con la cookie. Devuelve `null` si la sesión ya no vale (401) o la cuenta
 * dejó de ser administradora (403); cualquier otro fallo se lanza para no cerrar la sesión
 * por un problema de red.
 */
export async function webRefresh(): Promise<WebTokens | null> {
  const response = await post("refresh");
  if (response.status === HTTP_UNAUTHORIZED || response.status === HTTP_FORBIDDEN) {
    return null;
  }
  if (!response.ok) {
    throw await toApiError(response);
  }
  return toTokens(response);
}

export async function webLogout(): Promise<void> {
  const response = await post("logout");
  if (!response.ok) {
    throw await toApiError(response);
  }
}
