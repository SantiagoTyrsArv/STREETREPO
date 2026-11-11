import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { API, apiError, server } from "../test/server";
import { ApiError, createApiClient, NETWORK_ERROR_MESSAGE } from "./client";

type Overrides = Partial<Parameters<typeof createApiClient>[0]>;

function makeClient(overrides: Overrides = {}) {
  return createApiClient({
    baseUrl: API,
    getAccessToken: () => "vigente",
    refresh: async () => null,
    onSessionEnded: () => {},
    ...overrides,
  });
}

/** Ruta que solo acepta el token «nuevo»; con cualquier otro responde 401. */
function onlyAcceptsNewToken() {
  server.use(
    http.get(`${API}/api/v1/things/:id`, ({ request, params }) =>
      request.headers.get("Authorization") === "Bearer nuevo"
        ? HttpResponse.json({ id: params.id })
        : apiError(401, "UNAUTHORIZED", "Debes iniciar sesión para continuar."),
    ),
  );
}

describe("cliente de la API", () => {
  it("single_refresh_for_concurrent_401s: un solo refresco para varias peticiones con 401", async () => {
    onlyAcceptsNewToken();
    let token = "vencido";
    const refresh = vi.fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
      token = "nuevo";
      return token;
    });
    const onSessionEnded = vi.fn();
    const client = makeClient({ getAccessToken: () => token, refresh, onSessionEnded });

    const results = await Promise.all(
      ["1", "2", "3"].map((id) => client.get<{ id: string }>(`/api/v1/things/${id}`)),
    );

    expect(results).toEqual([{ id: "1" }, { id: "2" }, { id: "3" }]);
    expect(refresh).toHaveBeenCalledTimes(1);
    expect(onSessionEnded).not.toHaveBeenCalled();
  });

  it("no refresca de nuevo si otra petición ya renovó el acceso", async () => {
    onlyAcceptsNewToken();
    let token = "vencido";
    const refresh = vi.fn(async () => {
      token = "nuevo";
      return token;
    });
    const client = makeClient({ getAccessToken: () => token, refresh });
    // La petición lenta sale con el token vencido y recibe su 401 después del refresco.
    server.use(
      http.get(`${API}/api/v1/slow`, async ({ request }) => {
        if (request.headers.get("Authorization") === "Bearer nuevo") {
          return HttpResponse.json({ ok: true });
        }
        await new Promise((resolve) => setTimeout(resolve, 40));
        return apiError(401, "UNAUTHORIZED", "Debes iniciar sesión para continuar.");
      }),
    );

    const slow = client.get<{ ok: boolean }>("/api/v1/slow");
    await client.get("/api/v1/things/1");

    await expect(slow).resolves.toEqual({ ok: true });
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("session_ended_when_refresh_fails: sin refresco, avisa y lanza el 401", async () => {
    onlyAcceptsNewToken();
    const onSessionEnded = vi.fn();
    const client = makeClient({ refresh: async () => null, onSessionEnded });

    const failure = client.get("/api/v1/things/1");

    await expect(failure).rejects.toBeInstanceOf(ApiError);
    await expect(failure).rejects.toMatchObject({ status: 401, code: "UNAUTHORIZED" });
    expect(onSessionEnded).toHaveBeenCalledTimes(1);
  });

  it("no cierra la sesión si el refresco falla por la red", async () => {
    onlyAcceptsNewToken();
    const onSessionEnded = vi.fn();
    const networkFailure = new ApiError(0, "NETWORK_ERROR", NETWORK_ERROR_MESSAGE);
    const client = makeClient({
      refresh: async () => {
        throw networkFailure;
      },
      onSessionEnded,
    });

    await expect(client.get("/api/v1/things/1")).rejects.toBe(networkFailure);
    expect(onSessionEnded).not.toHaveBeenCalled();
  });

  it("network_error_message: un fallo de red se explica en español", async () => {
    server.use(http.get(`${API}/api/v1/things/:id`, () => HttpResponse.error()));

    await expect(makeClient().get("/api/v1/things/1")).rejects.toMatchObject({
      status: 0,
      code: "NETWORK_ERROR",
      message: "No hay conexión con el servidor. Revisa tu red e intenta de nuevo.",
    });
  });

  it("conserva el código, el mensaje y los detalles del error de la API", async () => {
    server.use(
      http.put(`${API}/api/v1/admin/weights`, () =>
        apiError(409, "WEIGHTS_VERSION_CONFLICT", "Otra persona guardó pesos nuevos.", {
          current_version_id: 7,
        }),
      ),
    );

    await expect(makeClient().put("/api/v1/admin/weights", {})).rejects.toMatchObject({
      status: 409,
      code: "WEIGHTS_VERSION_CONFLICT",
      message: "Otra persona guardó pesos nuevos.",
      details: { current_version_id: 7 },
    });
  });

  it("un error sin el formato de la API recibe un mensaje genérico", async () => {
    server.use(
      http.get(`${API}/api/v1/things/:id`, () => new HttpResponse("<html>", { status: 502 })),
    );

    await expect(makeClient().get("/api/v1/things/1")).rejects.toMatchObject({
      status: 502,
      code: "UNKNOWN_ERROR",
      message: "Ocurrió un error inesperado. Intenta de nuevo.",
    });
  });

  it("envía el token, la consulta sin valores vacíos y el cuerpo en JSON", async () => {
    let seen: { auth: string | null; search: string; body: unknown } | null = null;
    server.use(
      http.get(`${API}/api/v1/admin/ranking`, ({ request }) => {
        seen = {
          auth: request.headers.get("Authorization"),
          search: new URL(request.url).search,
          body: null,
        };
        return HttpResponse.json({ items: [] });
      }),
      http.patch(`${API}/api/v1/admin/reports/9/status`, async ({ request }) => {
        seen = { auth: null, search: "", body: await request.json() };
        return HttpResponse.json({ ok: true });
      }),
    );
    const client = makeClient();

    await client.get("/api/v1/admin/ranking", { limit: 20, offset: 0, status: undefined });
    expect(seen).toEqual({ auth: "Bearer vigente", search: "?limit=20&offset=0", body: null });

    await client.patch("/api/v1/admin/reports/9/status", { status: "priorizado" });
    expect(seen).toMatchObject({ body: { status: "priorizado" } });
  });

  it("repite el parámetro de consulta por cada valor de una lista", async () => {
    let search = "";
    server.use(
      http.get(`${API}/api/v1/admin/ranking`, ({ request }) => {
        search = new URL(request.url).search;
        return HttpResponse.json({ items: [] });
      }),
    );

    await makeClient().get("/api/v1/admin/ranking", { status: ["evaluado", "priorizado"] });
    expect(search).toBe("?status=evaluado&status=priorizado");

    await makeClient().get("/api/v1/admin/ranking", { status: [], limit: 20 });
    expect(search).toBe("?limit=20");
  });

  it("una respuesta 204 no devuelve cuerpo", async () => {
    server.use(http.put(`${API}/api/v1/things/1`, () => new HttpResponse(null, { status: 204 })));

    await expect(makeClient().put("/api/v1/things/1", {})).resolves.toBeUndefined();
  });

  it("getBlob devuelve los bytes de la imagen", async () => {
    server.use(
      http.get(`${API}/api/v1/reports/9/photo`, () =>
        HttpResponse.arrayBuffer(new Uint8Array([1, 2, 3]).buffer, {
          headers: { "Content-Type": "image/jpeg" },
        }),
      ),
    );

    const blob = await makeClient().getBlob("/api/v1/reports/9/photo");

    expect(blob.size).toBe(3);
  });
});
