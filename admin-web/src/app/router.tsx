import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "../auth/LoginPage";
import { LOGIN_PATH, RequireRole } from "../auth/RequireRole";
import { HOME_PATHS } from "../auth/roles";
import { useSession } from "../auth/SessionProvider";
import { LoadingView } from "../components/StateViews";
import { ComparisonPage } from "../features/comparison/ComparisonPage";
import { EvaluationPage } from "../features/evaluation/EvaluationPage";
import { EvaluationZonePage } from "../features/evaluation/EvaluationZonePage";
import { PrioritizationPage } from "../features/prioritization/PrioritizationPage";
import { ReportDetailPage } from "../features/report-detail/ReportDetailPage";
import { WeightsPage } from "../features/weights/WeightsPage";
import { Layout } from "./Layout";

/** Con sesión abierta, el inicio de sesión lleva a la pantalla de inicio del rol. */
function LoginRoute() {
  const { status, user } = useSession();
  return status === "signed-in" && user !== null ? (
    <Navigate to={HOME_PATHS[user.role]} replace />
  ) : (
    <LoginPage />
  );
}

/** La raíz lleva a la pantalla de inicio del rol, o al inicio de sesión. */
function HomeRedirect() {
  const { status, user } = useSession();
  if (status === "checking") {
    return <LoadingView />;
  }
  return <Navigate to={user === null ? LOGIN_PATH : HOME_PATHS[user.role]} replace />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path={LOGIN_PATH} element={<LoginRoute />} />
      <Route path="/" element={<HomeRedirect />} />
      <Route element={<RequireRole staffRole="administrador" />}>
        <Route element={<Layout />}>
          <Route path={HOME_PATHS.administrador} element={<PrioritizationPage />} />
          <Route path="/reportes/:id" element={<ReportDetailPage />} />
          <Route path="/pesos" element={<WeightsPage />} />
          <Route path="/comparacion" element={<ComparisonPage />} />
        </Route>
      </Route>
      <Route element={<RequireRole staffRole="evaluador" />}>
        <Route element={<Layout />}>
          <Route path={HOME_PATHS.evaluador} element={<EvaluationPage />} />
          <Route path="/evaluacion/zonas/:zoneId" element={<EvaluationZonePage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
