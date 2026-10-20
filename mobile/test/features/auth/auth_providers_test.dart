import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/config/app_config.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/session.dart';

import '../../support/fake_http_adapter.dart';
import '../../support/memory_token_store.dart';

void main() {
  late FakeHttpAdapter adapter;
  late MemoryTokenStore store;

  ProviderContainer container() {
    final c = ProviderContainer.test(
      overrides: [
        appConfigProvider.overrideWithValue(AppConfig.parse('http://api.test')),
        tokenStoreProvider.overrideWithValue(store),
      ],
    );
    c.read(apiClientProvider).httpClientAdapter = adapter;
    return c;
  }

  setUp(() {
    adapter = FakeHttpAdapter();
    store = MemoryTokenStore(const AuthTokens(access: 'vencido', refresh: 'r1'));
    adapter.on('GET', '/me', (options) async {
      return options.headers['Authorization'] == 'Bearer nuevo'
          ? const FakeResponse(
              200,
              body: {'id': 'u1', 'name': 'Ana', 'email': 'ana@correo.co', 'role': 'ciudadano'},
            )
          : FakeResponse(401, body: errorBody('INVALID_TOKEN'));
    });
  });

  test('con el acceso vencido, refresca por la API y recupera la sesión', () async {
    adapter.reply(
      'POST',
      '/auth/refresh',
      const FakeResponse(
        200,
        body: {'access_token': 'nuevo', 'expires_in': 900, 'refresh_token': 'r2'},
      ),
    );

    final state = await container().read(sessionControllerProvider.future);

    expect(state, isA<SignedIn>());
    expect(await store.read(), const AuthTokens(access: 'nuevo', refresh: 'r2'));
    expect(adapter.count('POST', '/auth/refresh'), 1);
  });

  test('si el refresco es rechazado, la sesión termina con el aviso', () async {
    adapter.reply(
      'POST',
      '/auth/refresh',
      FakeResponse(401, body: errorBody('INVALID_REFRESH_TOKEN')),
    );
    final c = container();

    final state = await c.read(sessionControllerProvider.future);

    expect(state, isA<SignedOut>().having((s) => s.sessionExpired, 'expirada', isTrue));
    expect(c.read(sessionControllerProvider).value, isA<SignedOut>());
    expect(await store.read(), isNull);
    expect(adapter.count('POST', '/auth/refresh'), 1);
  });
}
