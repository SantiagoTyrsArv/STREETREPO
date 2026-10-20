import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/core/routing/app_router.dart';
import 'package:street_repo/features/auth/domain/session.dart';

import '../../support/fake_auth_repository.dart';

void main() {
  const signedOut = AsyncData<SessionState>(SignedOut());
  const expired = AsyncData<SessionState>(SignedOut(sessionExpired: true));
  const signedIn = AsyncData<SessionState>(SignedIn(testUser));

  test('mientras se recupera la sesión todo lleva a la pantalla de inicio', () {
    const loading = AsyncLoading<SessionState>();
    expect(redirectForSession(loading, AppRoutes.myReports), AppRoutes.startup);
    expect(redirectForSession(loading, AppRoutes.startup), isNull);
  });

  test('sin red al abrir se queda en la pantalla de inicio para reintentar', () {
    const failed = AsyncError<SessionState>(NetworkFailure(), StackTrace.empty);
    expect(redirectForSession(failed, AppRoutes.login), AppRoutes.startup);
  });

  test('fuera de sesión, las rutas privadas llevan a la Bienvenida', () {
    expect(redirectForSession(signedOut, AppRoutes.myReports), AppRoutes.welcome);
    expect(redirectForSession(signedOut, AppRoutes.startup), AppRoutes.welcome);
    expect(redirectForSession(signedOut, AppRoutes.reportDetailOf('r1')), AppRoutes.welcome);
  });

  test('fuera de sesión, las rutas de acceso y la política se quedan', () {
    for (final route in [
      AppRoutes.welcome,
      AppRoutes.register,
      AppRoutes.login,
      AppRoutes.privacyPolicy,
    ]) {
      expect(redirectForSession(signedOut, route), isNull, reason: route);
    }
  });

  test('si la sesión venció, lleva a «Ingresar» en vez de la Bienvenida', () {
    expect(redirectForSession(expired, AppRoutes.myReports), AppRoutes.login);
  });

  test('en sesión, las rutas de acceso llevan a «Mis reportes»', () {
    expect(redirectForSession(signedIn, AppRoutes.login), AppRoutes.myReports);
    expect(redirectForSession(signedIn, AppRoutes.welcome), AppRoutes.myReports);
    expect(redirectForSession(signedIn, AppRoutes.startup), AppRoutes.myReports);
    expect(redirectForSession(signedIn, AppRoutes.newReport), isNull);
    expect(redirectForSession(signedIn, AppRoutes.privacyPolicy), isNull);
  });
}
