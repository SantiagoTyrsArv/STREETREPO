import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import type { ApiClient } from "../api/client";
import { fakeApi, fakeSession, WithSession } from "./session";

function LocationProbe() {
  const location = useLocation();
  return <p data-testid="location">{location.pathname}</p>;
}

type Options = {
  api?: Partial<ApiClient>;
  /** Ruta inicial y patrón de la pantalla bajo prueba. */
  path?: string;
  route?: string;
};

/**
 * Monta una pantalla con sesión de mentira, caché de consultas sin reintentos y rutas en
 * memoria. Cualquier otra ruta muestra su dirección en `data-testid="location"`.
 */
export function renderScreen(ui: ReactNode, { api = {}, path = "/", route = "/" }: Options = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <WithSession session={fakeSession({ api: fakeApi(api) })}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path={route} element={ui} />
            <Route path="*" element={<LocationProbe />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </WithSession>,
  );
}
