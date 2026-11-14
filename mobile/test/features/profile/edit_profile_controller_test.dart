import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/session.dart';
import 'package:street_repo/features/profile/application/edit_profile_controller.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/memory_token_store.dart';

void main() {
  late FakeAuthRepository auth;
  late ProviderContainer c;

  EditProfileController controller() => c.read(editProfileControllerProvider.notifier);
  EditProfileState state() => c.read(editProfileControllerProvider);

  setUp(() async {
    final store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store);
    c = ProviderContainer.test(
      overrides: [
        tokenStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(auth),
      ],
    );
    await c.read(sessionControllerProvider.future);
    c.listen(editProfileControllerProvider, (_, _) {});
  });

  test('cambiar solo el nombre no pide contraseña y actualiza la sesión', () async {
    expect(controller().emailChanged(' ana@correo.co '), isFalse);

    await controller().submit(name: ' Ana María ', email: 'ana@correo.co');

    expect(auth.updated, (name: 'Ana María', email: null, currentPassword: null));
    expect(state().saved, isTrue);
    final session = c.read(sessionControllerProvider).value! as SignedIn;
    expect(session.user.name, 'Ana María');
  });

  test('cambiar el correo envía la contraseña actual', () async {
    expect(controller().emailChanged('nueva@correo.co'), isTrue);

    await controller().submit(
      name: 'Ana',
      email: 'nueva@correo.co',
      currentPassword: 'una-clave-larga',
    );

    expect(auth.updated, (
      name: null,
      email: 'nueva@correo.co',
      currentPassword: 'una-clave-larga',
    ));
    expect(state().saved, isTrue);
  });

  test('cambiar el correo sin contraseña no llama a la API', () async {
    await controller().submit(name: 'Ana', email: 'nueva@correo.co');

    expect(state().passwordError, 'Escribe tu contraseña actual.');
    expect(auth.calls, isNot(contains('updateProfile')));
  });

  test('sin cambios no llama a la API y da por guardado', () async {
    await controller().submit(name: 'Ana', email: 'ana@correo.co');

    expect(state().saved, isTrue);
    expect(auth.calls, isNot(contains('updateProfile')));
  });

  test('nombre vacío o correo inválido se marcan sin llamar a la API', () async {
    await controller().submit(name: '  ', email: 'no-es-correo');

    expect(state().nameError, 'Escribe tu nombre.');
    expect(state().emailError, 'Escribe un correo válido.');
    expect(auth.calls, isNot(contains('updateProfile')));
  });

  test('la contraseña incorrecta se muestra como error de contraseña', () async {
    auth.updateFailure = const ApiError(
      status: 403,
      code: 'PASSWORD_CONFIRMATION_FAILED',
      message: 'La contraseña actual no es correcta.',
    );

    await controller().submit(name: 'Ana', email: 'nueva@correo.co', currentPassword: 'mala');

    expect(state().passwordError, 'La contraseña actual no es correcta.');
    expect(state().saved, isFalse);
    expect((c.read(sessionControllerProvider).value! as SignedIn).user.email, 'ana@correo.co');
  });

  test('demasiados intentos se muestran como error de contraseña', () async {
    auth.updateFailure = const ApiError(
      status: 429,
      code: 'TOO_MANY_LOGIN_ATTEMPTS',
      message: 'Demasiados intentos fallidos. Espera un momento e intenta de nuevo.',
    );

    await controller().submit(name: 'Ana', email: 'nueva@correo.co', currentPassword: 'mala');

    expect(state().passwordError, startsWith('Demasiados intentos'));
  });

  test('un correo que ya es de otra cuenta se marca en el campo', () async {
    auth.updateFailure = const ApiError(
      status: 409,
      code: 'EMAIL_ALREADY_REGISTERED',
      message: 'Ya existe una cuenta con ese correo.',
    );

    await controller().submit(name: 'Ana', email: 'otra@correo.co', currentPassword: 'clave');

    expect(state().emailError, 'Ya existe una cuenta con ese correo.');
    expect(state().passwordError, isNull);
  });

  test('un error de validación del servidor marca el campo', () async {
    auth.updateFailure = const ApiError(
      status: 422,
      code: 'VALIDATION_ERROR',
      message: 'Datos inválidos.',
      details: {
        'fields': [
          {'field': 'name'},
        ],
      },
    );

    await controller().submit(name: 'A', email: 'ana@correo.co');

    expect(state().nameError, 'Revisa tu nombre.');
    expect(state().error, isNull);
  });

  test('sin red muestra el mensaje de conexión y conserva los datos', () async {
    auth.updateFailure = const NetworkFailure();

    await controller().submit(name: 'Otra', email: 'ana@correo.co');

    expect(state().error, const NetworkFailure().message);
    expect(state().submitting, isFalse);
  });
}
