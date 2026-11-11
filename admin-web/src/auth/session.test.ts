import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, apiError, server } from "../test/server";
import { webLogin, webLogout, webRefresh } from "./session";

const TOKENS = { access_token: "acceso", token_type: "bearer", expires_in: 900 };

describe("sesión web del panel", () => {
  it("webLogin envía la cabecera anti-CSRF y devuelve el acceso", async () => {
    let csrf: string | null = null;
    let body: unknown = null;
    server.use(
      http.post(`${API}/api/v1/auth/web/login`, async ({ request }) => {
        csrf = request.headers.get("X-CSRF-Protection");
        body = await request.json();
        return HttpResponse.json(TOKENS);
      }),
    );

    const result = await webLogin("ana@pasto.gov.co", "secreta");

    expect(result).toEqual({ accessToken: "acceso", expiresIn: 900 });
    expect(csrf).toBe("1");
    expect(body).toEqual({ email: "ana@pasto.gov.co", password: "secreta" });
  });

  it("webLogin lanza el error de la API", async () => {
    server.use(
      http.post(`${API}/api/v1/auth/web/login`, () =>
        apiError(401, "INVALID_CREDENTIALS", "Correo o contraseña incorrectos."),
      ),
    );

    await expect(webLogin("ana@pasto.gov.co", "mala")).rejects.toMatchObject({
      status: 401,
      code: "INVALID_CREDENTIALS",
    });
  });

  it("webRefresh devuelve el acceso nuevo", async () => {
    let csrf: string | null = null;
    server.use(
      http.post(`${API}/api/v1/auth/web/refresh`, ({ request }) => {
        csrf = request.headers.get("X-CSRF-Protection");
        return HttpResponse.json(TOKENS);
      }),
    );

    await expect(webRefresh()).resolves.toEqual({ accessToken: "acceso", expiresIn: 900 });
    expect(csrf).toBe("1");
  });

  it.each([
    [401, "INVALID_SESSION"],
    [403, "ADMIN_ROLE_REQUIRED"],
  ])("webRefresh devuelve null cuando la sesión ya no vale (%i)", async (status, code) => {
    server.use(
      http.post(`${API}/api/v1/auth/web/refresh`, () => apiError(status, code, "Sin sesión.")),
    );

    await expect(webRefresh()).resolves.toBeNull();
  });

  it("webRefresh no confunde un fallo del servidor con una sesión terminada", async () => {
    server.use(http.post(`${API}/api/v1/auth/web/refresh`, () => HttpResponse.error()));

    await expect(webRefresh()).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  it("webLogout llama a la API con la cabecera anti-CSRF", async () => {
    let csrf: string | null = null;
    server.use(
      http.post(`${API}/api/v1/auth/web/logout`, ({ request }) => {
        csrf = request.headers.get("X-CSRF-Protection");
        return new HttpResponse(null, { status: 204 });
      }),
    );

    await expect(webLogout()).resolves.toBeUndefined();
    expect(csrf).toBe("1");
  });
});
