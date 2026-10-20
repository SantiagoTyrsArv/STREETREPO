import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/config/app_config.dart';
import 'package:street_repo/core/network/api_client.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/data/token_store.dart';

import '../../support/fake_http_adapter.dart';
import '../../support/memory_token_store.dart';

void main() {
  late FakeHttpAdapter adapter;
  late MemoryTokenStore store;
  late int refreshCalls;
  late int expirations;
  late Dio dio;

  Dio build({Future<AuthTokens> Function(String refresh)? refresh}) {
    final client = buildApiClient(
      AppConfig.parse('http://api.test'),
      store,
      refresh ??
          (token) async {
            refreshCalls++;
            // Deja que las demás peticiones fallen mientras el refresco está en vuelo.
            await Future<void>.delayed(const Duration(milliseconds: 20));
            return const AuthTokens(access: 'nuevo', refresh: 'refresco-2');
          },
      () => expirations++,
    );
    client.httpClientAdapter = adapter;
    return client;
  }

  setUp(() {
    adapter = FakeHttpAdapter();
    store = MemoryTokenStore(const AuthTokens(access: 'viejo', refresh: 'refresco-1'));
    refreshCalls = 0;
    expirations = 0;
    adapter.on('GET', '/me/reports', (options) async {
      final bearer = options.headers['Authorization'];
      return bearer == 'Bearer nuevo'
          ? const FakeResponse(200, body: {'items': <Object?>[]})
          : FakeResponse(401, body: errorBody('INVALID_TOKEN'));
    });
    dio = build();
  });

  test('añade el token salvo en las rutas de autenticación', () async {
    adapter.reply('POST', '/auth/login', const FakeResponse(200, body: {}));

    await dio.post<Object?>('/auth/login', data: {'email': 'a@b.co'});
    await dio
        .get<Object?>('/me/reports')
        .catchError((_) => Response<Object?>(requestOptions: RequestOptions()));

    final login = adapter.requests.firstWhere((r) => r.uri.path.endsWith('/auth/login'));
    final reports = adapter.requests.firstWhere((r) => r.uri.path.endsWith('/me/reports'));
    expect(login.headers.containsKey('Authorization'), isFalse);
    expect(reports.headers['Authorization'], 'Bearer viejo');
    expect(login.uri.toString(), 'http://api.test/api/v1/auth/login');
  });

  test('tres 401 simultáneos hacen un solo refresco y las tres se reintentan', () async {
    final responses = await Future.wait([
      dio.get<Object?>('/me/reports'),
      dio.get<Object?>('/me/reports'),
      dio.get<Object?>('/me/reports'),
    ]);

    expect(refreshCalls, 1);
    expect(responses.map((r) => r.statusCode), [200, 200, 200]);
    expect(await store.read(), const AuthTokens(access: 'nuevo', refresh: 'refresco-2'));
  });

  test('reintenta un envío con foto (multipart) tras refrescar', () async {
    adapter.on('POST', '/reports', (options) async {
      return options.headers['Authorization'] == 'Bearer nuevo'
          ? const FakeResponse(201, body: {'id': 'r1'})
          : FakeResponse(401, body: errorBody('INVALID_TOKEN'));
    });

    final response = await dio.post<Object?>(
      '/reports',
      data: FormData.fromMap({
        'severity': 'alta',
        'photo': MultipartFile.fromBytes([1, 2, 3], filename: 'foto.jpg'),
      }),
    );

    expect(response.statusCode, 201);
    expect(refreshCalls, 1);
    expect(adapter.count('POST', '/reports'), 2);
  });

  test('si el servidor rechaza el refresco, borra la sesión y avisa una sola vez', () async {
    dio = build(
      refresh: (_) async {
        refreshCalls++;
        throw const ApiError(
          status: 401,
          code: 'INVALID_REFRESH_TOKEN',
          message: 'Sesión no válida',
        );
      },
    );

    final results = await Future.wait([
      dio.get<Object?>('/me/reports').then<Object?>((r) => r, onError: (Object e) => e),
      dio.get<Object?>('/me/reports').then<Object?>((r) => r, onError: (Object e) => e),
    ]);

    expect(results, everyElement(isA<DioException>()));
    expect(refreshCalls, 1);
    expect(expirations, 1);
    expect(await store.read(), isNull);
    // Sin bucles: cada petición se intentó una sola vez.
    expect(adapter.count('GET', '/me/reports'), 2);
  });

  test('si el refresco falla por red, conserva la sesión y devuelve el error de red', () async {
    dio = build(
      refresh: (_) async {
        refreshCalls++;
        await Future<void>.delayed(const Duration(milliseconds: 20));
        throw DioException(
          requestOptions: RequestOptions(path: '/auth/refresh'),
          type: DioExceptionType.connectionError,
        );
      },
    );

    final results = await Future.wait([
      dio.get<Object?>('/me/reports').then<Object?>((r) => r, onError: (Object e) => e),
      dio.get<Object?>('/me/reports').then<Object?>((r) => r, onError: (Object e) => e),
    ]);

    expect(refreshCalls, 1);
    expect(expirations, 0);
    expect(await store.read(), const AuthTokens(access: 'viejo', refresh: 'refresco-1'));
    for (final result in results) {
      expect(ApiFailure.fromDioException(result! as DioException), isA<NetworkFailure>());
    }
  });

  test('un error del servidor al refrescar tampoco cierra la sesión', () async {
    dio = build(
      refresh: (_) async {
        refreshCalls++;
        throw const UnexpectedFailure();
      },
    );

    final error = await dio
        .get<Object?>('/me/reports')
        .then<Object?>((r) => r, onError: (Object e) => e);

    expect(ApiFailure.fromDioException(error! as DioException), isA<UnexpectedFailure>());
    expect(expirations, 0);
    expect(await store.read(), isNotNull);
  });

  test('sin sesión guardada un 401 no intenta refrescar', () async {
    store = MemoryTokenStore(null);
    dio = build();

    await expectLater(dio.get<Object?>('/me/reports'), throwsA(isA<DioException>()));
    expect(refreshCalls, 0);
  });
}
