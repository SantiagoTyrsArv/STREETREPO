import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/session.dart';
import 'auth_providers.dart';

/// Política vigente según el servidor (`GET /privacy-policy`).
final privacyPolicyProvider = FutureProvider<PrivacyPolicy>(
  (ref) => ref.watch(authRepositoryProvider).privacyPolicy(),
  // La pantalla ofrece «Reintentar»; no se reintenta a ciegas.
  retry: (_, _) => null,
);

/// Versión de la política que el ciudadano aceptó en esta sesión de la app. La aceptación
/// es de una versión concreta: si el servidor publica otra, la casilla queda sin marcar.
final policyConsentProvider = NotifierProvider<PolicyConsentController, String?>(
  PolicyConsentController.new,
);

class PolicyConsentController extends Notifier<String?> {
  @override
  String? build() => null;

  void accept(String version) => state = version;

  void revoke() => state = null;
}
