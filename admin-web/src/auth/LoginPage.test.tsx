import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ApiError, NETWORK_ERROR_MESSAGE } from "../api/client";
import { fakeSession, WithSession } from "../test/session";
import type { Session } from "./SessionProvider";
import { LoginPage } from "./LoginPage";

function renderLogin(overrides: Partial<Session> = {}) {
  const session = fakeSession({ status: "signed-out", user: null, ...overrides });
  render(
    <WithSession session={session}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </WithSession>,
  );
  return session;
}

async function submit(email = "ana@pasto.gov.co", password = "una-clave-larga") {
  await userEvent.type(screen.getByLabelText("Correo institucional"), email);
  await userEvent.type(screen.getByLabelText("Contraseña"), password);
  await userEvent.click(screen.getByRole("button", { name: "Ingresar" }));
}

function failingWith(error: ApiError) {
  return vi.fn(async () => {
    throw error;
  });
}

describe("inicio de sesión de funcionarios", () => {
  it("muestra los textos del diseño", () => {
    renderLogin();

    expect(screen.getByRole("heading", { name: "Ingreso de funcionarios" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Acceso solo para cuentas de funcionario. Las cuentas las crea el administrador del sistema.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Acceso protegido: los intentos fallidos se limitan por correo y por dirección IP.",
      ),
    ).toBeInTheDocument();
  });

  it("inicia sesión con el correo y la contraseña escritos", async () => {
    const session = renderLogin();

    await submit(" ana@pasto.gov.co ", "una-clave-larga");

    expect(session.signIn).toHaveBeenCalledWith("ana@pasto.gov.co", "una-clave-larga");
  });

  it("shows_invalid_credentials_message: 401 no dice cuál de los dos datos falló", async () => {
    renderLogin({
      signIn: failingWith(new ApiError(401, "INVALID_CREDENTIALS", "Credenciales inválidas")),
    });

    await submit();

    expect(await screen.findByRole("alert")).toHaveTextContent("Correo o contraseña incorrectos.");
    // Lo escrito se conserva para corregirlo (guía 10.3).
    expect(screen.getByLabelText("Correo institucional")).toHaveValue("ana@pasto.gov.co");
  });

  it("shows_admin_role_required_message: una cuenta de ciudadano no entra", async () => {
    renderLogin({
      signIn: failingWith(new ApiError(403, "ADMIN_ROLE_REQUIRED", "Sin acceso")),
    });

    await submit();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Esta cuenta no tiene acceso al panel.",
    );
  });

  it("shows_lockout_minutes: 429 muestra la espera y bloquea el envío", async () => {
    renderLogin({
      signIn: failingWith(
        new ApiError(429, "TOO_MANY_LOGIN_ATTEMPTS", "Demasiados intentos", {
          retry_after_s: 272,
        }),
      ),
    });

    await submit();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Demasiados intentos fallidos");
    expect(alert).toHaveTextContent("Espera 4 min 32 s antes de intentarlo de nuevo.");
    expect(screen.getByRole("button", { name: "Reintentar en 4:32" })).toBeDisabled();
  });

  it("un fallo de red muestra el mensaje del cliente", async () => {
    renderLogin({
      signIn: failingWith(new ApiError(0, "NETWORK_ERROR", NETWORK_ERROR_MESSAGE)),
    });

    await submit();

    expect(await screen.findByRole("alert")).toHaveTextContent(NETWORK_ERROR_MESSAGE);
  });

  it("disables_submit_while_sending: no permite el envío doble", async () => {
    let finish: () => void = () => {};
    const signIn = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        }),
    );
    renderLogin({ signIn });

    await submit();

    const sending = screen.getByRole("button", { name: "Ingresando…" });
    expect(sending).toBeDisabled();
    await userEvent.click(sending);
    expect(signIn).toHaveBeenCalledTimes(1);
    finish();
    expect(await screen.findByRole("button", { name: "Ingresar" })).toBeEnabled();
  });

  it("avisa cuando la sesión anterior terminó", () => {
    renderLogin({ notice: "Tu sesión terminó. Inicia sesión de nuevo." });

    expect(screen.getByRole("status")).toHaveTextContent(
      "Tu sesión terminó. Inicia sesión de nuevo.",
    );
  });
});
