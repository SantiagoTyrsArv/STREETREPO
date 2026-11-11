import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "../auth/LoginPage";
import { LOGIN_PATH, RequireAdmin } from "../auth/RequireAdmin";
import { useSession } from "../auth/SessionProvider";
import { EmptyView } from "../components/StateViews";
import { PrioritizationPage } from "../features/prioritization/PrioritizationPage";
import { ReportDetailPage } from "../features/report-detail/ReportDetailPage";
import { Layout } from "./Layout";

const HOME_PATH = "/priorizacion";

/** Con sesión abierta, el inicio de sesión lleva al panel. */
function LoginRoute() {
  const { status } = useSession();
  return status === "signed-in" ? <Navigate to={HOME_PATH} replace /> : <LoginPage />;
}

/** Marcador de la pantalla que llega en las tarea 10 del plan de la fase 6. */
function PendingScreen({ title }: { title: string }) {
  return <EmptyView title={title} detail="Esta pantalla está en construcción." />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path={LOGIN_PATH} element={<LoginRoute />} />
      <Route element={<RequireAdmin />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to={HOME_PATH} replace />} />
          <Route path={HOME_PATH} element={<PrioritizationPage />} />
          <Route path="/reportes/:id" element={<ReportDetailPage />} />
          <Route path="/pesos" element={<PendingScreen title="Pesos del modelo" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
