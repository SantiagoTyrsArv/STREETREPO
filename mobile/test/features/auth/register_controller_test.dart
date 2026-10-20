import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/privacy_policy_providers.dart';
import 'package:street_repo/features/auth/application/register_controller.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/domain/session.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/memory_token_store.dart';

const _policy = PrivacyPolicy(version: '1.0');
const _password = 'una-clave-larga';

void main() {
  late FakeAuthRepository auth;
  late ProviderContainer c;

  Future<void> submit({String name = 'Ana', String email = 'ana@correo.co'}) => c
      .read(registerControllerProvider.notifier)
      .submit(name: name, email: email, password: _password, policy: _policy);

  setUp(() async {
    final store = MemoryTokenStore();
    auth = FakeAuthRepository(store);
    c = ProviderContainer.test(
      overrides: [
        tokenStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(auth),
      ],
    );
    await c.read(sessionControllerProvider.future);
    c.listen(registerControllerProvider, (_, _) {});
  });

  test('registra con la versión aceptada y luego inicia sesión', () async {
    c.read(policyConsentProvider.notifier).accept('1.0');

    await submit();

    expect(auth.calls, ['register', 'login', 'me']);
    expect(auth.registeredPolicyVersion, '1.0');
    expect(c.read(sessionControllerProvider).value, isA<SignedIn>());
    // El consentimiento queda guardado en el servidor; aquí ya no hace falta.
    expect(c.read(policyConsentProvider), isNull);
  });

  test('valida en el celular antes de llamar a la API', () async {
    await c
        .read(registerControllerProvider.notifier)
        .submit(name: '  ', email: 'sin-arroba', password: 'corta', policy: _policy);

    final state = c.read(registerControllerProvider);
    expect(state.nameError, isNotNull);
    expect(state.emailError, isNotNull);
    expect(state.passwordError, 'La contraseña debe tener de 12 a 128 caracteres.');
    expect(auth.calls, isEmpty);
  });

  test('un correo ya registrado se muestra en el campo del correo', () async {
    auth.registerFailure = const ApiError(
      status: 409,
      code: 'EMAIL_ALREADY_REGISTERED',
      message: 'Ya existe una cuenta con ese correo.',
    );

    await submit();

    final state = c.read(registerControllerProvider);
    expect(state.emailError, 'Ya existe una cuenta con ese correo.');
    expect(state.error, isNull);
    expect(state.submitting, isFalse);
  });

  test('una contraseña débil se muestra en el campo de la contraseña', () async {
    auth.registerFailure = const ApiError(
      status: 422,
      code: 'WEAK_PASSWORD',
      message: 'La contraseña debe tener al menos 12 caracteres.',
    );

    await submit();

    expect(
      c.read(registerControllerProvider).passwordError,
      'La contraseña debe tener al menos 12 caracteres.',
    );
  });

  test('si la política cambió, la recarga y la casilla queda sin marcar', () async {
    c.read(policyConsentProvider.notifier).accept('1.0');
    await c.read(privacyPolicyProvider.future);
    auth
      ..registerFailure = const ApiError(
        status: 409,
        code: 'POLICY_VERSION_OUTDATED',
        message: 'La política de datos cambió.',
      )
      ..onPrivacyPolicy = () async => const PrivacyPolicy(version: '2.0');

    await submit();

    expect(c.read(registerControllerProvider).error, 'La política de datos cambió.');
    final reloaded = await c.read(privacyPolicyProvider.future);
    expect(reloaded.version, '2.0');
    expect(c.read(policyConsentProvider) == reloaded.version, isFalse);
  });

  test('si se creó la cuenta pero no pudo entrar, lo indica para ir a «Ingresar»', () async {
    auth.loginFailure = const NetworkFailure();

    await submit();

    expect(c.read(registerControllerProvider).accountCreated, isTrue);
    expect(c.read(sessionControllerProvider).value, isA<SignedOut>());
  });

  test('sin red al registrar muestra el mensaje de conexión', () async {
    auth.registerFailure = const NetworkFailure();

    await submit();

    expect(c.read(registerControllerProvider).error, const NetworkFailure().message);
  });
}
