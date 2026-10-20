import 'session.dart';

/// Acceso y cuenta del ciudadano. Los fallos llegan como `ApiFailure`.
abstract interface class AuthRepository {
  Future<PrivacyPolicy> privacyPolicy();

  /// Registra la cuenta con el consentimiento de [policyVersion]. No inicia sesión: el
  /// registro no devuelve tokens.
  Future<void> register({
    required String name,
    required String email,
    required String password,
    required String policyVersion,
  });

  /// Inicia sesión y guarda los tokens.
  Future<void> login({required String email, required String password});

  /// Cierra la sesión en el servidor si se puede y **siempre** borra los tokens locales.
  Future<void> logout();

  Future<UserProfile> me();
}
