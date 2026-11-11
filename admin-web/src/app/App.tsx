import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter } from "react-router-dom";
import { SessionProvider } from "../auth/SessionProvider";
import { AppRoutes } from "./router";

/** Raíz del panel: caché de datos del servidor, sesión y rutas. */
export function App() {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      {/* Al terminar la sesión no queda en memoria nada de lo consultado (guía 7.2). */}
      <SessionProvider onSessionCleared={() => queryClient.clear()}>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </SessionProvider>
    </QueryClientProvider>
  );
}
