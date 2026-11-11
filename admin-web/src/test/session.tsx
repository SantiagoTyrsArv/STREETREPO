import type { ReactNode } from "react";
import { vi } from "vitest";
import type { ApiClient } from "../api/client";
import { SessionContext, type Session } from "../auth/SessionProvider";

/** Cliente de la API de mentira; cada prueba sustituye lo que usa. */
export function fakeApi(overrides: Partial<ApiClient> = {}): ApiClient {
  const unexpected = () => Promise.reject(new Error("Llamada a la API no prevista en la prueba"));
  return { get: unexpected, patch: unexpected, put: unexpected, getBlob: unexpected, ...overrides };
}

export function fakeSession(overrides: Partial<Session> = {}): Session {
  return {
    status: "signed-in",
    user: { name: "Ana Funcionaria" },
    notice: null,
    signIn: vi.fn(async () => {}),
    signOut: vi.fn(async () => {}),
    api: fakeApi(),
    ...overrides,
  };
}

/** Envuelve la interfaz con una sesión fija, sin red. */
export function WithSession({ session, children }: { session: Session; children: ReactNode }) {
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}
