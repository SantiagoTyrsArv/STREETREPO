/// Par de tokens de la sesión: acceso (15 min) y refresco rotatorio (guía 7.1).
class AuthTokens {
  const AuthTokens({required this.access, required this.refresh});

  final String access;
  final String refresh;

  @override
  bool operator ==(Object other) =>
      other is AuthTokens && other.access == access && other.refresh == refresh;

  @override
  int get hashCode => Object.hash(access, refresh);

  // Nunca imprimir los tokens (guía 7.3).
  @override
  String toString() => 'AuthTokens(***)';
}

abstract interface class TokenStore {
  Future<AuthTokens?> read();

  Future<void> write(AuthTokens tokens);

  Future<void> clear();
}
