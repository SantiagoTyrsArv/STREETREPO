import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/session.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/memory_token_store.dart';

void main() {
  late MemoryTokenStore store;
  late FakeAuthRepository auth;

  ProviderContainer container() => ProviderContainer.test(
    overrides: [
      tokenStoreProvider.overrideWithValue(store),
      authRepositoryProvider.overrideWithValue(auth),
    ],
  );

  setUp(() {
    store = MemoryTokenStore();
    auth = FakeAuthRepository(store);
  });

  test('sin tokens guardados queda fuera de sesión sin llamar a la API', () async {
    final state = await container().read(sessionControllerProvider.future);

    expect(state, isA<SignedOut>().having((s) => s.sessionExpired, 'expirada', isFalse));
    expect(auth.calls, isEmpty);
  });

  test('con tokens guardados y perfil disponible queda en sesión', () async {
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store);

    final state = await container().read(sessionControllerProvider.future);

    expect(state, isA<SignedIn>().having((s) => s.user.name, 'nombre', 'Ana'));
  });

  test('con tokens rechazados (401) borra la sesión y avisa que terminó', () async {
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store)
      ..onMe = () async =>
          throw const ApiError(status: 401, code: 'INVALID_TOKEN', message: 'Sesión no válida');

    final state = await container().read(sessionControllerProvider.future);

    expect(state, isA<SignedOut>().having((s) => s.sessionExpired, 'expirada', isTrue));
    expect(await store.read(), isNull);
  });

  test('sin red al abrir conserva los tokens y permite reintentar', () async {
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store)..onMe = () async => throw const NetworkFailure();
    final c = container();

    await expectLater(c.read(sessionControllerProvider.future), throwsA(isA<NetworkFailure>()));
    expect(c.read(sessionControllerProvider).error, isA<NetworkFailure>());
    expect(await store.read(), isNotNull);

    auth.onMe = () async => testUser;
    await c.read(sessionControllerProvider.notifier).restore();

    expect(c.read(sessionControllerProvider).value, isA<SignedIn>());
  });

  test('iniciar sesión deja el perfil en la sesión', () async {
    final c = container();
    await c.read(sessionControllerProvider.future);

    await c
        .read(sessionControllerProvider.notifier)
        .signIn(email: 'ana@correo.co', password: 'clave');

    expect(c.read(sessionControllerProvider).value, isA<SignedIn>());
    expect(auth.calls, ['login', 'me']);
  });

  test('un inicio de sesión fallido llega a quien lo llamó y no cambia el estado', () async {
    auth.loginFailure = const ApiError(
      status: 401,
      code: 'INVALID_CREDENTIALS',
      message: 'Correo o contraseña incorrectos.',
    );
    final c = container();
    await c.read(sessionControllerProvider.future);

    await expectLater(
      c.read(sessionControllerProvider.notifier).signIn(email: 'a@b.co', password: 'mala'),
      throwsA(isA<ApiError>()),
    );
    expect(c.read(sessionControllerProvider).value, isA<SignedOut>());
  });

  test('cerrar sesión sin red igual queda fuera de sesión y sin tokens', () async {
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store)..logoutFailure = const NetworkFailure();
    final c = container();
    await c.read(sessionControllerProvider.future);

    await c.read(sessionControllerProvider.notifier).signOut();

    expect(
      c.read(sessionControllerProvider).value,
      isA<SignedOut>().having((s) => s.sessionExpired, 'expirada', isFalse),
    );
    expect(await store.read(), isNull);
  });

  test('cuando el cliente HTTP avisa que la sesión venció, queda fuera con el aviso', () async {
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store);
    final c = container();
    await c.read(sessionControllerProvider.future);

    c.read(sessionControllerProvider.notifier).expire();

    expect(
      c.read(sessionControllerProvider).value,
      isA<SignedOut>().having((s) => s.sessionExpired, 'expirada', isTrue),
    );
  });
}
