/** Cliente HTTP de la API: token de acceso en memoria, un solo refresco ante un 401 y errores uniformes. */

export const NETWORK_ERROR_MESSAGE =
  "No hay conexión con el servidor. Revisa tu red e intenta de nuevo.";
const UNKNOWN_ERROR_MESSAGE = "Ocurrió un error inesperado. Intenta de nuevo.";

const HTTP_UNAUTHORIZED = 401;
const HTTP_NO_CONTENT = 204;
/** Estado que se usa cuando no hubo respuesta del servidor. */
const NO_RESPONSE_STATUS = 0;

/** Error de la API con su código estable (guía 6.1) o un fallo de red (`NETWORK_ERROR`). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Convierte una respuesta de error en `ApiError`, aunque el cuerpo no sea el de la API. */
export async function toApiError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null);
  if (isRecord(body) && typeof body.code === "string" && typeof body.message === "string") {
    return new ApiError(
      response.status,
      body.code,
      body.message,
      isRecord(body.details) ? body.details : {},
    );
  }
  return new ApiError(response.status, "UNKNOWN_ERROR", UNKNOWN_ERROR_MESSAGE);
}

/** `fetch` que traduce la falta de respuesta (sin red, CORS, servidor caído) a `ApiError`. */
export async function fetchOrNetworkError(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch {
    throw new ApiError(NO_RESPONSE_STATUS, "NETWORK_ERROR", NETWORK_ERROR_MESSAGE);
  }
}

type QueryValue = string | number | boolean | null | undefined;
/** Una lista repite el parámetro (`status=a&status=b`); los valores vacíos no se envían. */
export type QueryParams = Record<string, QueryValue | readonly string[]>;

export type ApiClient = {
  get<T>(path: string, query?: QueryParams): Promise<T>;
  patch<T>(path: string, body: unknown): Promise<T>;
  put<T>(path: string, body: unknown): Promise<T>;
  getBlob(path: string): Promise<Blob>;
};

export type ApiClientOptions = {
  /** Origen de la API, sin barra final. */
  baseUrl: string;
  getAccessToken: () => string | null;
  /** Renueva el acceso. `null` significa que la sesión terminó; un fallo de red se lanza. */
  refresh: () => Promise<string | null>;
  onSessionEnded: () => void;
};

function buildUrl(baseUrl: string, path: string, query?: QueryParams): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (Array.isArray(value)) {
      value.forEach((item: string) => params.append(key, item));
    } else if (value !== undefined && value !== null) {
      params.set(key, String(value));
    }
  }
  const search = params.toString();
  return `${baseUrl}${path}${search ? `?${search}` : ""}`;
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const { baseUrl, getAccessToken, refresh, onSessionEnded } = options;
  let refreshing: Promise<string | null> | null = null;

  /** Varias peticiones con 401 comparten el mismo refresco: la cookie rota en cada uso. */
  function refreshOnce(): Promise<string | null> {
    refreshing ??= refresh().finally(() => {
      refreshing = null;
    });
    return refreshing;
  }

  async function send(method: string, url: string, body?: unknown): Promise<Response> {
    const attempt = (token: string | null) => {
      const headers = new Headers();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      if (body !== undefined) {
        headers.set("Content-Type", "application/json");
      }
      return fetchOrNetworkError(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    };

    const usedToken = getAccessToken();
    let response = await attempt(usedToken);
    if (response.status === HTTP_UNAUTHORIZED) {
      // Si otra petición ya renovó el acceso mientras esta viajaba, basta con reintentar.
      const current = getAccessToken();
      const token = current !== null && current !== usedToken ? current : await refreshOnce();
      if (token === null) {
        onSessionEnded();
        throw await toApiError(response);
      }
      response = await attempt(token);
      if (response.status === HTTP_UNAUTHORIZED) {
        onSessionEnded();
      }
    }
    if (!response.ok) {
      throw await toApiError(response);
    }
    return response;
  }

  async function json<T>(response: Response): Promise<T> {
    if (response.status === HTTP_NO_CONTENT) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  return {
    get: async <T>(path: string, query?: QueryParams) =>
      json<T>(await send("GET", buildUrl(baseUrl, path, query))),
    patch: async <T>(path: string, body: unknown) =>
      json<T>(await send("PATCH", buildUrl(baseUrl, path), body)),
    put: async <T>(path: string, body: unknown) =>
      json<T>(await send("PUT", buildUrl(baseUrl, path), body)),
    getBlob: async (path: string) => (await send("GET", buildUrl(baseUrl, path))).blob(),
  };
}
