import { Navigate, Outlet } from "react-router-dom";
import { LoadingView } from "../components/StateViews";
import { HOME_PATHS, type StaffRole } from "./roles";
import { useSession } from "./SessionProvider";

export const LOGIN_PATH = "/ingresar";

/**
 * Rutas de un rol: sin sesión lleva al inicio de sesión y con el otro rol, a su propia pantalla
 * de inicio. La API vuelve a verificar el rol en cada ruta (`/admin` o `/evaluation`).
 */
export function RequireRole({ staffRole }: { staffRole: StaffRole }) {
  const { status, user } = useSession();
  if (status === "checking") {
    return <LoadingView />;
  }
  if (status === "signed-out" || user === null) {
    return <Navigate to={LOGIN_PATH} replace />;
  }
  if (user.role !== staffRole) {
    return <Navigate to={HOME_PATHS[user.role]} replace />;
  }
  return <Outlet />;
}
