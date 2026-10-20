import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/network/api_error.dart';

import '../../support/fake_http_adapter.dart';

Future<ApiFailure> _failureFor(FakeResponse response) async {
  final adapter = FakeHttpAdapter()..reply('GET', '/x', response);
  final dio = Dio(BaseOptions(baseUrl: 'http://api.test'))..httpClientAdapter = adapter;
  try {
    await dio.get<Object?>('/x');
  } on DioException catch (e) {
    return ApiFailure.fromDioException(e);
  }
  throw StateError('La petición no falló');
}

void main() {
  test('lee el formato de error uniforme de la API', () async {
    final failure = await _failureFor(
      FakeResponse(
        409,
        body: errorBody(
          'EMAIL_ALREADY_REGISTERED',
          message: 'Ese correo ya tiene una cuenta.',
          details: {'field': 'email'},
        ),
      ),
    );

    expect(failure, isA<ApiError>());
    final error = failure as ApiError;
    expect(error.status, 409);
    expect(error.code, 'EMAIL_ALREADY_REGISTERED');
    expect(error.message, 'Ese correo ya tiene una cuenta.');
    expect(error.details['field'], 'email');
    expect(error.retryAfter, isNull);
  });

  test('lee Retry-After de un 429', () async {
    final failure = await _failureFor(
      FakeResponse(
        429,
        body: errorBody('TOO_MANY_LOGIN_ATTEMPTS'),
        headers: {
          'retry-after': ['120'],
        },
      ),
    );

    expect((failure as ApiError).retryAfter, const Duration(seconds: 120));
  });

  test('sin conexión es NetworkFailure con un mensaje en español', () {
    final failure = ApiFailure.fromDioException(
      DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.connectionError,
      ),
    );

    expect(failure, isA<NetworkFailure>());
    expect(failure.message, 'No hay conexión. Revisa tu señal e intenta de nuevo.');
  });

  test('un tiempo agotado también es NetworkFailure', () {
    final failure = ApiFailure.fromDioException(
      DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.receiveTimeout,
      ),
    );

    expect(failure, isA<NetworkFailure>());
  });

  test('una respuesta sin el formato esperado es UnexpectedFailure', () async {
    final failure = await _failureFor(const FakeResponse(502, body: 'Bad Gateway'));

    expect(failure, isA<UnexpectedFailure>());
    expect(failure.message, isNotEmpty);
  });
}
