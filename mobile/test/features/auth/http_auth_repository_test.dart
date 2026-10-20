import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/data/auth_api.dart';
import 'package:street_repo/features/auth/data/http_auth_repository.dart';
import 'package:street_repo/features/auth/data/token_store.dart';

import '../../support/fake_http_adapter.dart';
import '../../support/memory_token_store.dart';

const _tokensBody = {
  'access_token': 'acceso',
  'token_type': 'bearer',
  'expires_in': 900,
  'refresh_token': 'refresco',
};

void main() {
  late FakeHttpAdapter adapter;
  late MemoryTokenStore store;
  late AuthApi api;
  late HttpAuthRepository repository;

  setUp(() {
    adapter = FakeHttpAdapter();
    store = MemoryTokenStore();
    final dio = Dio(BaseOptions(baseUrl: 'http://api.test/api/v1'))..httpClientAdapter = adapter;
    api = AuthApi(dio);
    repository = HttpAuthRepository(api, store);
  });

  test('el registro envía el consentimiento con la versión de la política', () async {
    adapter.reply('POST', '/auth/register', const FakeResponse(201, body: {}));

    await repository.register(
      name: 'Ana',
      email: 'ana@correo.co',
      password: 'una-clave-larga',
      policyVersion: '1.0',
    );

    final body = adapter.requests.single.data as Map<String, Object?>;
    expect(body['accepted_policy'], isTrue);
    expect(body['policy_version'], '1.0');
    expect(body['email'], 'ana@correo.co');
  });

  test('el registro con correo repetido es un ApiError con su código', () async {
    adapter.reply(
      'POST',
      '/auth/register',
      FakeResponse(409, body: errorBody('EMAIL_ALREADY_REGISTERED')),
    );

    await expectLater(
      repository.register(name: 'Ana', email: 'a@b.co', password: 'x', policyVersion: '1.0'),
      throwsA(isA<ApiError>().having((e) => e.code, 'code', 'EMAIL_ALREADY_REGISTERED')),
    );
  });

  test('el inicio de sesión guarda los tokens', () async {
    adapter.reply('POST', '/auth/login', const FakeResponse(200, body: _tokensBody));

    await repository.login(email: 'ana@correo.co', password: 'una-clave-larga');

    expect(await store.read(), const AuthTokens(access: 'acceso', refresh: 'refresco'));
  });

  test('credenciales incorrectas no guardan nada', () async {
    adapter.reply('POST', '/auth/login', FakeResponse(401, body: errorBody('INVALID_CREDENTIALS')));

    await expectLater(
      repository.login(email: 'a@b.co', password: 'mala'),
      throwsA(isA<ApiError>().having((e) => e.status, 'status', 401)),
    );
    expect(await store.read(), isNull);
  });

  test('cerrar sesión envía el refresco y borra los tokens', () async {
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    repository = HttpAuthRepository(api, store);
    adapter.reply('POST', '/auth/logout', const FakeResponse(204));

    await repository.logout();

    expect((adapter.requests.single.data as Map<String, Object?>)['refresh_token'], 'r');
    expect(await store.read(), isNull);
  });

  test('cerrar sesión sin red igual borra los tokens', () async {
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    repository = HttpAuthRepository(api, store);
    adapter.on(
      'POST',
      '/auth/logout',
      (options) =>
          throw DioException(requestOptions: options, type: DioExceptionType.connectionError),
    );

    await expectLater(repository.logout(), throwsA(isA<NetworkFailure>()));
    expect(await store.read(), isNull);
  });

  test('lee el perfil del titular', () async {
    adapter.reply(
      'GET',
      '/me',
      const FakeResponse(
        200,
        body: {
          'id': 'u1',
          'name': 'Ana',
          'email': 'ana@correo.co',
          'role': 'ciudadano',
          'registered_at': '2026-10-19T15:00:00Z',
          'policy_version': '1.0',
          'policy_accepted_at': '2026-10-19T15:00:00Z',
        },
      ),
    );

    final user = await repository.me();

    expect(user.id, 'u1');
    expect(user.name, 'Ana');
    expect(user.role, 'ciudadano');
  });

  test('una respuesta con otra forma es UnexpectedFailure', () async {
    adapter.reply('GET', '/me', const FakeResponse(200, body: {'id': 7}));

    await expectLater(repository.me(), throwsA(isA<UnexpectedFailure>()));
  });

  test('lee la política vigente, con o sin texto publicado', () async {
    adapter.reply(
      'GET',
      '/privacy-policy',
      const FakeResponse(200, body: {'version': '1.0', 'url': null}),
    );

    final policy = await repository.privacyPolicy();

    expect(policy.version, '1.0');
    expect(policy.url, isNull);
  });

  test('el refresco cambia el token de refresco por un par nuevo', () async {
    adapter.reply('POST', '/auth/refresh', const FakeResponse(200, body: _tokensBody));

    final tokens = await api.refresh('viejo');

    expect(tokens, const AuthTokens(access: 'acceso', refresh: 'refresco'));
    expect((adapter.requests.single.data as Map<String, Object?>)['refresh_token'], 'viejo');
  });
}
