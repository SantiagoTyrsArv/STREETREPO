import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

/// Rutas de la app. Las pantallas se completan en las tareas siguientes del plan.
abstract final class AppRoutes {
  static const welcome = '/bienvenida';
  static const register = '/registro';
  static const privacyPolicy = '/politica';
  static const login = '/ingresar';
  static const myReports = '/mis-reportes';
  static const newReport = '/reportar';
  static const profile = '/perfil';
  static const reportDetail = '/reportes/:id';

  static String reportDetailOf(String id) => '/reportes/$id';
}

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: AppRoutes.welcome,
    routes: [
      for (final path in [
        AppRoutes.welcome,
        AppRoutes.register,
        AppRoutes.privacyPolicy,
        AppRoutes.login,
        AppRoutes.myReports,
        AppRoutes.newReport,
        AppRoutes.profile,
        AppRoutes.reportDetail,
      ])
        GoRoute(
          path: path,
          builder: (context, state) => const Scaffold(body: Placeholder()),
        ),
    ],
  );
});
