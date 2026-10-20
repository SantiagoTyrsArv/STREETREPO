import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/login_controller.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/domain/session.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/memory_token_store.dart';

void main() {
  late MemoryTokenStore store;
  late FakeAuthRepository auth;
  late ProviderContainer c;

  setUp(() async {
    store = MemoryTokenStore();
    auth = FakeAuthRepository(store);
    c = ProviderContainer.test(
      overrides: [
        tokenStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(auth),
      ],
    );
    await c.read(sessionControllerProvider.future);
    // Mantiene vivo el proveedor autoDispose durante la prueba.
    c.listen(loginControllerProvider, (_, _) {});
  });

  test('un inicio correcto deja la sesión abierta sin errores', () async {
    await c
        .read(loginControllerProvider.notifier)
        .submit(email: '  ana@correo.co ', password: 'clave');

    expect(auth.loggedInEmail, 'ana@correo.co');
    expect(c.read(sessionControllerProvider).value, isA<SignedIn>());
    expect(c.read(loginControllerProvider).error, isNull);
  });

  test('credenciales incorrectas muestran el mensaje del servidor', () async {
    auth.loginFailure = const ApiError(
      status: 401,
      code: 'INVALID_CREDENTIALS',
      message: 'Correo o contraseña incorrectos.',
    );

    await c.read(loginControllerProvider.notifier).submit(email: 'a@b.co', password: 'mala');

    final state = c.read(loginControllerProvider);
    expect(state.error, 'Correo o contraseña incorrectos.');
    expect(state.submitting, isFalse);
    expect(state.locked, isFalse);
  });

  test('sin red muestra el mensaje de conexión', () async {
    auth.loginFailure = const NetworkFailure();

    await c.read(loginControllerProvider.notifier).submit(email: 'a@b.co', password: 'x');

    expect(c.read(loginControllerProvider).error, const NetworkFailure().message);
  });

  test('un 429 bloquea con el tiempo de Retry-After y no deja reintentar', () async {
    auth.loginFailure = const ApiError(
      status: 429,
      code: 'TOO_MANY_LOGIN_ATTEMPTS',
      message: 'Demasiados intentos fallidos.',
      retryAfter: Duration(seconds: 90),
    );
    final login = c.read(loginControllerProvider.notifier);

    await login.submit(email: 'a@b.co', password: 'x');
    await login.submit(email: 'a@b.co', password: 'x');

    expect(c.read(loginControllerProvider).lockRemaining, const Duration(seconds: 90));
    expect(auth.calls.where((call) => call == 'login'), hasLength(1));
  });
}
