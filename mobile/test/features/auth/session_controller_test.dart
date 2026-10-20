import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/auth_repository.dart';
import 'package:street_repo/features/auth/domain/session.dart';

import '../../support/memory_token_store.dart';

const _user = UserProfile(id: 'u1', name: 'Ana', email: 'ana@correo.co', role: 'ciudadano');

/// Repositorio falso: cada operación hace lo que se le indique y registra las llamadas.
class FakeAuthRepository implements AuthRepository {
  FakeAuthRepository(this.store);

  final MemoryTokenStore store;
  final List<String> calls = [];
  Future<UserProfile> Function() onMe = () async => _user;
  ApiFailure? loginFailure;
  ApiFailure? logoutFailure;
  String? registeredPolicyVersion;

  @override
  Future<PrivacyPolicy> privacyPolicy() async => const PrivacyPolicy(version: '1.0');

  @override
  Future<void> register({
    required String name,
    required String email,
    required String password,
    required String policyVersion,
  }) async {
    calls.add('register');
    registeredPolicyVersion = policyVersion;
  }

  @override
  Future<void> login({required String email, required String password}) async {
    calls.add('login');
    if (loginFailure != null) throw loginFailure!;
    await store.write(const AuthTokens(access: 'a', refresh: 'r'));
  }

  @override
  Future<void> logout() async {
    calls.add('logout');
    await store.clear();
    if (logoutFailure != null) throw logoutFailure!;
  }

  @override
  Future<UserProfile> me() {
    calls.add('me');
    return onMe();
  }
}

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

    auth.onMe = () async => _user;
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

  test('registrarse acepta la política indicada y luego inicia sesión', () async {
    final c = container();
    await c.read(sessionControllerProvider.future);

    await c
        .read(sessionControllerProvider.notifier)
        .register(name: 'Ana', email: 'ana@correo.co', password: 'clave', policyVersion: '1.0');

    expect(auth.calls, ['register', 'login', 'me']);
    expect(auth.registeredPolicyVersion, '1.0');
    expect(c.read(sessionControllerProvider).value, isA<SignedIn>());
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
