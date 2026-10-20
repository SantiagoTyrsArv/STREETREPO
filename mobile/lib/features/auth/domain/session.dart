/// Política de tratamiento de datos vigente (Ley 1581). `url` es null mientras no se haya
/// publicado el texto (solo en desarrollo).
class PrivacyPolicy {
  const PrivacyPolicy({required this.version, this.url});

  final String version;
  final Uri? url;
}

/// Datos del propio titular, tal como los devuelve `GET /me`.
class UserProfile {
  const UserProfile({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
  });

  final String id;
  final String name;
  final String email;
  final String role;
}

/// Estado de la sesión. Mientras se recupera la sesión guardada, el proveedor está en
/// `AsyncLoading`; no hace falta un estado «desconocido» propio.
sealed class SessionState {
  const SessionState();
}

final class SignedOut extends SessionState {
  const SignedOut({this.sessionExpired = false});

  /// La sesión terminó sin que el ciudadano la cerrara (refresco rechazado o vencido).
  final bool sessionExpired;
}

final class SignedIn extends SessionState {
  const SignedIn(this.user);

  final UserProfile user;
}
