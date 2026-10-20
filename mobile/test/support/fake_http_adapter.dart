import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

/// Respuesta preparada para [FakeHttpAdapter].
class FakeResponse {
  const FakeResponse(this.status, {this.body, this.headers = const {}});

  final int status;
  final Object? body;
  final Map<String, List<String>> headers;
}

typedef FakeHandler = Future<FakeResponse> Function(RequestOptions options);

/// Adaptador HTTP en memoria: responde según `MÉTODO /ruta` y registra cada petición.
class FakeHttpAdapter implements HttpClientAdapter {
  final Map<String, FakeHandler> _handlers = {};
  final List<RequestOptions> requests = [];

  void on(String method, String path, FakeHandler handler) {
    _handlers['$method $path'] = handler;
  }

  void reply(String method, String path, FakeResponse response) {
    on(method, path, (_) async => response);
  }

  int count(String method, String path) =>
      requests.where((r) => r.method == method && r.uri.path.endsWith(path)).length;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    final key = _handlers.keys.firstWhere(
      (k) {
        final [method, path] = k.split(' ');
        return method == options.method && options.uri.path.endsWith(path);
      },
      orElse: () =>
          throw StateError('Sin respuesta preparada para ${options.method} ${options.uri}'),
    );
    final response = await _handlers[key]!(options);
    final body = response.body == null ? '' : jsonEncode(response.body);
    return ResponseBody.fromString(
      body,
      response.status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
        ...response.headers,
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

Map<String, Object?> errorBody(String code, {String message = 'Error', Object? details}) => {
  'code': code,
  'message': message,
  'details': details ?? <String, Object?>{},
};
