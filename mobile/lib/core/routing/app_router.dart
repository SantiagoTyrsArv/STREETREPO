import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/application/session_controller.dart';
import '../../features/auth/domain/session.dart';
import '../../features/auth/presentation/login_screen.dart';
import '../../features/auth/presentation/privacy_policy_screen.dart';
import '../../features/auth/presentation/register_screen.dart';
import '../../features/auth/presentation/startup_screen.dart';
import '../../features/auth/presentation/welcome_screen.dart';
import '../../features/my_reports/presentation/my_reports_screen.dart';
import '../../features/my_reports/presentation/report_detail_screen.dart';
import '../../features/profile/presentation/profile_screen.dart';
import '../../features/report_new/presentation/duplicate_screen.dart';
import '../../features/report_new/presentation/permission_denied_screen.dart';
import '../../features/report_new/presentation/permissions_screen.dart';
import '../../features/report_new/presentation/photo_location_screen.dart';
import '../../features/report_new/presentation/report_error_screens.dart';
import '../../features/report_new/presentation/report_sent_screen.dart';
import '../../features/report_new/presentation/severity_screen.dart';
import '../widgets/app_shell.dart';

/// Rutas de la app.
abstract final class AppRoutes {
  static const startup = '/inicio';
  static const welcome = '/bienvenida';
  static const register = '/registro';
  static const privacyPolicy = '/politica';
  static const login = '/ingresar';
  static const myReports = '/mis-reportes';
  static const newReport = '/reportar';
  static const newReportPermissions = '/reportar/permisos';
  static const newReportLocationDenied = '/reportar/sin-ubicacion';
  static const newReportSeverity = '/reportar/severidad';
  static const newReportDuplicates = '/reportar/duplicado';
  static const newReportSent = '/reportar/enviado';
  static const newReportOutsideArea = '/reportar/fuera-del-area';
  static const newReportRateLimited = '/reportar/limite';
  static const newReportPhotoRejected = '/reportar/foto-rechazada';
  static const profile = '/perfil';
  static const reportDetail = '/reportes/:id';

  static String reportDetailOf(String id) => '/reportes/$id';

  /// Rutas para quien no ha iniciado sesión.
  static const signedOutOnly = {welcome, register, login};
}

/// A dónde llevar al ciudadano según su sesión; null deja la navegación como está.
/// - Mientras se recupera la sesión (o si falló por red) → pantalla de inicio.
/// - Fuera de sesión → Bienvenida, o «Ingresar» si la sesión venció.
/// - En sesión, las rutas de acceso llevan a «Mis reportes».
/// La política es accesible en ambos casos.
String? redirectForSession(AsyncValue<SessionState> session, String location) {
  final state = switch (session) {
    AsyncData(:final value) => value,
    _ => null,
  };
  switch (state) {
    case null:
      return location == AppRoutes.startup ? null : AppRoutes.startup;
    case SignedOut(:final sessionExpired):
      if (AppRoutes.signedOutOnly.contains(location) || location == AppRoutes.privacyPolicy) {
        return null;
      }
      return sessionExpired ? AppRoutes.login : AppRoutes.welcome;
    case SignedIn():
      final onAccess = AppRoutes.signedOutOnly.contains(location) || location == AppRoutes.startup;
      return onAccess ? AppRoutes.myReports : null;
  }
}

final appRouterProvider = Provider<GoRouter>((ref) {
  // El enrutador se crea una vez; cada cambio de sesión vuelve a evaluar la redirección.
  final sessionChanged = ValueNotifier<int>(0);
  ref.listen(sessionControllerProvider, (_, _) => sessionChanged.value++);
  final router = GoRouter(
    initialLocation: AppRoutes.startup,
    refreshListenable: sessionChanged,
    redirect: (context, state) =>
        redirectForSession(ref.read(sessionControllerProvider), state.matchedLocation),
    routes: [
      GoRoute(path: AppRoutes.startup, builder: (context, state) => const StartupScreen()),
      GoRoute(path: AppRoutes.welcome, builder: (context, state) => const WelcomeScreen()),
      GoRoute(path: AppRoutes.register, builder: (context, state) => const RegisterScreen()),
      GoRoute(
        path: AppRoutes.privacyPolicy,
        builder: (context, state) => const PrivacyPolicyScreen(),
      ),
      GoRoute(
        path: AppRoutes.login,
        builder: (context, state) =>
            LoginScreen(createdAccountEmail: state.extra is String ? state.extra! as String : null),
      ),
      GoRoute(path: AppRoutes.newReport, builder: (context, state) => const PhotoLocationScreen()),
      GoRoute(
        path: AppRoutes.newReportPermissions,
        builder: (context, state) => const PermissionsScreen(),
      ),
      GoRoute(
        path: AppRoutes.newReportLocationDenied,
        builder: (context, state) => const PermissionDeniedScreen(),
      ),
      GoRoute(
        path: AppRoutes.newReportSeverity,
        builder: (context, state) => const SeverityScreen(),
      ),
      GoRoute(
        path: AppRoutes.newReportDuplicates,
        builder: (context, state) => const DuplicateScreen(),
      ),
      GoRoute(path: AppRoutes.newReportSent, builder: (context, state) => const ReportSentScreen()),
      GoRoute(
        path: AppRoutes.newReportOutsideArea,
        builder: (context, state) => const OutsideAreaScreen(),
      ),
      GoRoute(
        path: AppRoutes.newReportRateLimited,
        builder: (context, state) => const RateLimitedScreen(),
      ),
      GoRoute(
        path: AppRoutes.newReportPhotoRejected,
        builder: (context, state) => const PhotoRejectedScreen(),
      ),
      // Mis reportes y Perfil comparten la barra inferior; el detalle y el nuevo reporte se
      // abren a pantalla completa.
      ShellRoute(
        builder: (context, state, child) => AppShell(location: state.matchedLocation, child: child),
        routes: [
          GoRoute(
            path: AppRoutes.myReports,
            pageBuilder: (context, state) => const NoTransitionPage(child: MyReportsScreen()),
          ),
          GoRoute(
            path: AppRoutes.profile,
            pageBuilder: (context, state) => const NoTransitionPage(child: ProfileScreen()),
          ),
        ],
      ),
      GoRoute(
        path: AppRoutes.reportDetail,
        builder: (context, state) => ReportDetailScreen(reportId: state.pathParameters['id']!),
      ),
    ],
  );
  ref.onDispose(() {
    router.dispose();
    sessionChanged.dispose();
  });
  return router;
});
