import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/profile/application/delete_data_controller.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/memory_token_store.dart';

void main() {
  late MemoryTokenStore store;
  late FakeAuthRepository auth;
  late ProviderContainer c;

  DeleteDataController controller() => c.read(deleteDataControllerProvider.notifier);
  DeleteDataState state() => c.read(deleteDataControllerProvider);

  setUp(() {
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store);
    c = ProviderContainer.test(
      overrides: [
        tokenStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(auth),
      ],
    );
    c.listen(deleteDataControllerProvider, (_, _) {});
  });

  test('con la contraseña correcta guarda la constancia', () async {
    await controller().submit('una-clave-larga');

    expect(auth.deletionPassword, 'una-clave-larga');
    expect(state().receipt, same(testReceipt));
    expect(await store.read(), isNull);
  });

  test('sin contraseña no llama a la API', () async {
    await controller().submit('');

    expect(state().passwordError, 'Escribe tu contraseña actual.');
    expect(auth.calls, isEmpty);
  });

  test('la contraseña incorrecta no suprime nada', () async {
    auth.deletionFailure = const ApiError(
      status: 403,
      code: 'PASSWORD_CONFIRMATION_FAILED',
      message: 'La contraseña actual no es correcta.',
    );

    await controller().submit('mala');

    expect(state().passwordError, 'La contraseña actual no es correcta.');
    expect(state().receipt, isNull);
    expect(await store.read(), isNotNull);
  });

  test('demasiados intentos se muestran en el campo de contraseña', () async {
    auth.deletionFailure = const ApiError(
      status: 429,
      code: 'TOO_MANY_LOGIN_ATTEMPTS',
      message: 'Demasiados intentos fallidos. Espera un momento e intenta de nuevo.',
    );

    await controller().submit('mala');

    expect(state().passwordError, startsWith('Demasiados intentos'));
  });

  test('sin red muestra el mensaje de conexión y permite reintentar', () async {
    auth.deletionFailure = const NetworkFailure();
    await controller().submit('una-clave-larga');
    expect(state().error, const NetworkFailure().message);

    auth.deletionFailure = null;
    await controller().submit('una-clave-larga');

    expect(state().receipt, isNotNull);
  });

  test('con la constancia ya recibida no se vuelve a pedir la supresión', () async {
    await controller().submit('una-clave-larga');
    await controller().submit('una-clave-larga');

    expect(auth.calls.where((call) => call == 'requestDataDeletion'), hasLength(1));
  });
}
