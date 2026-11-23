import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { StrictMode } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../app/router";
import { API, apiError, server } from "../test/server";
import { fakeSession, WithSession } from "../test/session";
import {
  NOT_STAFF_MESSAGE,
  SessionProvider,
  useSession,
  type SessionUser,
} from "./SessionProvider";

// Estas pruebas son de rutas y sesión; las pantallas tienen las suyas.
vi.mock("../features/prioritization/PrioritizationPage", () => ({
  PrioritizationPage: () => <h1>Priorización de reportes</h1>,
}));

vi.mock("../features/weights/WeightsPage", () => ({
  WeightsPage: () => <h1>Pesos del modelo de priorización</h1>,
}));

vi.mock("../features/validation/ComparisonPage", () => ({
  ComparisonPage: () => <h1>Comparación con el panel de referencia</h1>,
}));

vi.mock("../features/evaluation/EvaluationPage", () => ({
  EvaluationPage: () => <h1>Mis evaluaciones</h1>,
}));

vi.mock("../features/evaluation/EvaluationZonePage", () => ({
  EvaluationZonePage: () => <h1>Ordenar la zona</h1>,
}));

const EVALUATOR: SessionUser = { name: "Eva Evaluadora", role: "evaluador" };

function renderAs(path: string, user: SessionUser = EVALUATOR) {
  render(
    <WithSession session={fakeSession({ user })}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </WithSession>,
  );
}

const TOKENS = { access_token: "acceso", token_type: "bearer", expires_in: 900 };
const ME = { id: "u-1", name: "Ana Funcionaria", email: "ana@pasto.gov.co", role: "administrador" };

function meRequiresToken() {
  return http.get(`${API}/api/v1/me`, ({ request }) =>
    request.headers.get("Authorization") === "Bearer acceso"
      ? HttpResponse.json(ME)
      : apiError(401, "UNAUTHORIZED", "Debes iniciar sesión para continuar."),
  );
}

function renderApp(path: string) {
  render(
    <StrictMode>
      <SessionProvider>
        <MemoryRouter initialEntries={[path]}>
          <AppRoutes />
        </MemoryRouter>
      </SessionProvider>
    </StrictMode>,
  );
}

describe("rutas protegidas", () => {
  it("redirects_to_login_when_signed_out: sin sesión lleva al inicio de sesión", () => {
    render(
      <WithSession session={fakeSession({ status: "signed-out", user: null })}>
        <MemoryRouter initialEntries={["/pesos"]}>
          <AppRoutes />
        </MemoryRouter>
      </WithSession>,
    );

    expect(screen.getByRole("heading", { name: "Ingreso de funcionarios" })).toBeInTheDocument();
  });

  it("mientras comprueba la sesión muestra la carga, no el inicio de sesión", () => {
    render(
      <WithSession session={fakeSession({ status: "checking", user: null })}>
        <MemoryRouter initialEntries={["/pesos"]}>
          <AppRoutes />
        </MemoryRouter>
      </WithSession>,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Cargando…");
    expect(screen.queryByRole("heading", { name: "Ingreso de funcionarios" })).toBeNull();
  });

  it("con sesión, el inicio de sesión lleva a Priorización", () => {
    render(
      <WithSession session={fakeSession()}>
        <MemoryRouter initialEntries={["/ingresar"]}>
          <AppRoutes />
        </MemoryRouter>
      </WithSession>,
    );

    expect(screen.getByRole("link", { name: "Priorización" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("restores_session_after_reload: el refresco web recupera la sesión", async () => {
    // StrictMode monta dos veces: aun así debe haber un solo refresco (la cookie rota).
    const refreshCalls = vi.fn();
    server.use(
      http.post(`${API}/api/v1/auth/web/refresh`, () => {
        refreshCalls();
        return HttpResponse.json(TOKENS);
      }),
      meRequiresToken(),
    );

    renderApp("/pesos");

    expect(await screen.findByText("Ana Funcionaria")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Pesos del modelo" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(refreshCalls).toHaveBeenCalledTimes(1);
  });

  it("sin cookie válida al cargar, muestra el inicio de sesión sin aviso", async () => {
    server.use(
      http.post(`${API}/api/v1/auth/web/refresh`, () =>
        apiError(401, "INVALID_SESSION", "Tu sesión terminó. Inicia sesión de nuevo."),
      ),
    );

    renderApp("/priorizacion");

    expect(
      await screen.findByRole("heading", { name: "Ingreso de funcionarios" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Tu sesión terminó. Inicia sesión de nuevo.")).toBeNull();
  });

  it("iniciar y cerrar sesión cambia entre el panel y el inicio de sesión", async () => {
    const logoutCalls = vi.fn();
    server.use(
      http.post(`${API}/api/v1/auth/web/refresh`, () =>
        apiError(401, "INVALID_SESSION", "Sin sesión."),
      ),
      http.post(`${API}/api/v1/auth/web/login`, () => HttpResponse.json(TOKENS)),
      http.post(`${API}/api/v1/auth/web/logout`, () => {
        logoutCalls();
        return new HttpResponse(null, { status: 204 });
      }),
      meRequiresToken(),
    );
    renderApp("/");

    await userEvent.type(await screen.findByLabelText("Correo institucional"), "ana@pasto.gov.co");
    await userEvent.type(screen.getByLabelText("Contraseña"), "una-clave-larga");
    await userEvent.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByText("Ana Funcionaria")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(
      await screen.findByRole("heading", { name: "Ingreso de funcionarios" }),
    ).toBeInTheDocument();
    expect(logoutCalls).toHaveBeenCalledTimes(1);
  });

  it("si el acceso y el refresco vencen, vuelve al inicio de sesión con el aviso", async () => {
    let refreshes = 0;
    server.use(
      http.post(`${API}/api/v1/auth/web/refresh`, () => {
        refreshes += 1;
        return refreshes === 1
          ? HttpResponse.json(TOKENS)
          : apiError(401, "INVALID_SESSION", "Tu sesión terminó. Inicia sesión de nuevo.");
      }),
      meRequiresToken(),
      http.get(`${API}/api/v1/admin/summary`, () =>
        apiError(401, "UNAUTHORIZED", "Debes iniciar sesión para continuar."),
      ),
    );

    function Probe() {
      const { api, status } = useSession();
      return status === "signed-in" ? (
        <button type="button" onClick={() => void api.get("/api/v1/admin/summary").catch(() => {})}>
          Consultar
        </button>
      ) : null;
    }

    render(
      <SessionProvider>
        <MemoryRouter initialEntries={["/priorizacion"]}>
          <AppRoutes />
          <Probe />
        </MemoryRouter>
      </SessionProvider>,
    );

    await userEvent.click(await screen.findByRole("button", { name: "Consultar" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Tu sesión terminó. Inicia sesión de nuevo.",
    );
    expect(screen.getByRole("heading", { name: "Ingreso de funcionarios" })).toBeInTheDocument();
  });
});

describe("rutas por rol", () => {
  it.each(["/priorizacion", "/pesos", "/comparacion", "/"])(
    "un evaluador que entra a %s es llevado a Mis evaluaciones",
    (path) => {
      renderAs(path);

      expect(screen.getByRole("heading", { name: "Mis evaluaciones" })).toBeInTheDocument();
    },
  );

  it("con sesión de evaluador, el inicio de sesión lleva a Mis evaluaciones", () => {
    renderAs("/ingresar");

    expect(screen.getByRole("heading", { name: "Mis evaluaciones" })).toBeInTheDocument();
  });

  it("un evaluador abre la zona que va a ordenar", () => {
    renderAs("/evaluacion/zonas/3");

    expect(screen.getByRole("heading", { name: "Ordenar la zona" })).toBeInTheDocument();
  });

  it.each(["/evaluacion", "/evaluacion/zonas/3"])(
    "un administrador que entra a %s es llevado a Priorización",
    (path) => {
      renderAs(path, { name: "Ana Funcionaria", role: "administrador" });

      expect(screen.getByRole("heading", { name: "Priorización de reportes" })).toBeInTheDocument();
    },
  );

  it("el administrador ve Comparación en el menú", () => {
    renderAs("/comparacion", { name: "Ana Funcionaria", role: "administrador" });

    const menu = screen.getByRole("navigation", { name: "Secciones del panel" });
    expect(
      within(menu)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(["Priorización", "Pesos del modelo", "Comparación"]);
    expect(screen.getByRole("link", { name: "Comparación" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("el menú del evaluador no muestra Priorización, Pesos ni Comparación", () => {
    renderAs("/evaluacion");

    const menu = screen.getByRole("navigation", { name: "Secciones del panel" });
    expect(
      within(menu)
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(["Mis evaluaciones"]);
    expect(screen.getByText("Panel de referencia")).toBeInTheDocument();
    expect(screen.queryByText("Sec. de Infraestructura")).toBeNull();
  });

  it("una cuenta que no es del personal no queda con sesión en el panel", async () => {
    const logoutCalls = vi.fn();
    server.use(
      http.post(`${API}/api/v1/auth/web/refresh`, () => HttpResponse.json(TOKENS)),
      http.get(`${API}/api/v1/me`, () => HttpResponse.json({ ...ME, role: "ciudadano" })),
      http.post(`${API}/api/v1/auth/web/logout`, () => {
        logoutCalls();
        return new HttpResponse(null, { status: 204 });
      }),
    );

    renderApp("/priorizacion");

    expect(await screen.findByText(NOT_STAFF_MESSAGE)).toHaveAttribute("role", "status");
    expect(logoutCalls).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("heading", { name: "Ingreso de funcionarios" })).toBeInTheDocument();
  });
});
