import 'package:dio/dio.dart';

/// Fallo de una llamada a la API, ya traducido para la interfaz. Los mensajes del servidor
/// vienen en español y se pueden mostrar tal cual (guía 6.1).
sealed class ApiFailure implements Exception {
  const ApiFailure();

  String get message;

  static ApiFailure fromDioException(DioException exception) {
    switch (exception.type) {
      case DioExceptionType.connectionError:
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.transformTimeout:
        return const NetworkFailure();
      case DioExceptionType.badResponse:
        return _fromResponse(exception.response) ?? const UnexpectedFailure();
      case DioExceptionType.badCertificate:
      case DioExceptionType.cancel:
      case DioExceptionType.unknown:
        return exception.error is ApiFailure
            ? exception.error! as ApiFailure
            : const UnexpectedFailure();
    }
  }

  static ApiError? _fromResponse(Response<dynamic>? response) {
    final body = response?.data;
    if (response == null || body is! Map<String, dynamic>) return null;
    final code = body['code'];
    final message = body['message'];
    if (code is! String || message is! String) return null;
    final details = body['details'];
    final retryAfter = int.tryParse(response.headers.value('retry-after') ?? '');
    return ApiError(
      status: response.statusCode ?? 0,
      code: code,
      message: message,
      details: details is Map<String, dynamic> ? details : const {},
      retryAfter: retryAfter == null ? null : Duration(seconds: retryAfter),
    );
  }
}

/// Error con el formato uniforme `{code, message, details}` de la API.
final class ApiError extends ApiFailure {
  const ApiError({
    required this.status,
    required this.code,
    required this.message,
    this.details = const {},
    this.retryAfter,
  });

  final int status;
  final String code;
  @override
  final String message;
  final Map<String, dynamic> details;
  final Duration? retryAfter;

  @override
  String toString() => 'ApiError($status $code)';
}

/// Sin conexión o tiempo agotado: se puede reintentar.
final class NetworkFailure extends ApiFailure {
  const NetworkFailure();

  @override
  String get message => 'No hay conexión. Revisa tu señal e intenta de nuevo.';
}

final class UnexpectedFailure extends ApiFailure {
  const UnexpectedFailure();

  @override
  String get message => 'Algo salió mal de nuestro lado. Intenta de nuevo en unos minutos.';
}
