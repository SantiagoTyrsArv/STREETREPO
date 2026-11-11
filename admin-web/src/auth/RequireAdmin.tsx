import { Navigate, Outlet } from "react-router-dom";
import { LoadingView } from "../components/StateViews";
import { useSession } from "./SessionProvider";

export const LOGIN_PATH = "/ingresar";

/**
 * Rutas del panel: solo con sesión. La sesión web solo se emite a administradores y cada
 * ruta `/admin` de la API vuelve a verificar el rol en el servidor.
 */
export function RequireAdmin() {
  const { status } = useSession();
  if (status === "checking") {
    return <LoadingView />;
  }
  if (status === "signed-out") {
    return <Navigate to={LOGIN_PATH} replace />;
  }
  return <Outlet />;
}
