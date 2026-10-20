import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_error.dart';
import '../domain/auth_repository.dart';
import '../domain/session.dart';
import 'auth_providers.dart';

final sessionControllerProvider = AsyncNotifierProvider<SessionController, SessionState>(
  SessionController.new,
  // Sin red al abrir la app, la pantalla ofrece «Reintentar»; no se reintenta a ciegas.
  retry: (_, _) => null,
);

/// Sesión del ciudadano. Los errores de [signIn] y [register] llegan a quien los llama
/// (la pantalla los muestra) y no cambian el estado.
class SessionController extends AsyncNotifier<SessionState> {
  AuthRepository get _auth => ref.read(authRepositoryProvider);

  @override
  Future<SessionState> build() {
    final expired = ref.read(sessionExpiredSignalProvider).stream.listen((_) => expire());
    ref.onDispose(expired.cancel);
    return _restore();
  }

  /// Vuelve a intentar recuperar la sesión guardada (p. ej. tras abrir la app sin red).
  Future<void> restore() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(_restore);
  }

  Future<void> signIn({required String email, required String password}) async {
    await _auth.login(email: email, password: password);
    state = AsyncData(SignedIn(await _auth.me()));
  }

  Future<void> register({
    required String name,
    required String email,
    required String password,
    required String policyVersion,
  }) async {
    await _auth.register(
      name: name,
      email: email,
      password: password,
      policyVersion: policyVersion,
    );
    await signIn(email: email, password: password);
  }

  /// Cierra la sesión aunque no haya red: los tokens locales se borran siempre.
  Future<void> signOut() async {
    try {
      await _auth.logout();
    } on ApiFailure {
      // El servidor no se enteró; el token de refresco vence solo.
    }
    state = const AsyncData(SignedOut());
  }

  /// Se llama cuando el cliente HTTP avisa que el refresco falló.
  void expire() => state = const AsyncData(SignedOut(sessionExpired: true));

  Future<SessionState> _restore() async {
    final tokens = ref.read(tokenStoreProvider);
    if (await tokens.read() == null) return const SignedOut();
    try {
      return SignedIn(await _auth.me());
    } on ApiError catch (e) {
      // Cualquier otro error (sin red, servidor caído) conserva los tokens para reintentar.
      if (e.status != 401) rethrow;
      await tokens.clear();
      return const SignedOut(sessionExpired: true);
    }
  }
}
