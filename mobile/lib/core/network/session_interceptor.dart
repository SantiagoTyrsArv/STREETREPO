import 'dart:async';

import 'package:dio/dio.dart';

import '../../features/auth/data/token_store.dart';

typedef RefreshTokens = Future<AuthTokens> Function(String refreshToken);

typedef RetryRequest = Future<Response<dynamic>> Function(RequestOptions options);

/// Añade el token de acceso y, ante un 401, refresca la sesión **una sola vez** aunque
/// fallen varias peticiones a la vez; las demás esperan ese refresco y se reintentan.
/// Si el refresco falla, borra la sesión y avisa una vez. Nunca reintenta en bucle.
class SessionInterceptor extends Interceptor {
  SessionInterceptor({
    required this._store,
    required this._refresh,
    required this._onSessionExpired,
    required this._retry,
  });

  static const _retriedKey = 'session_retried';

  final TokenStore _store;
  final RefreshTokens _refresh;
  final void Function() _onSessionExpired;
  final RetryRequest _retry;
  Future<AuthTokens?>? _refreshing;

  static bool _isAuthRoute(RequestOptions options) => options.path.startsWith('/auth/');

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    if (!_isAuthRoute(options)) {
      final tokens = await _store.read();
      if (tokens != null) options.headers['Authorization'] = 'Bearer ${tokens.access}';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    final options = err.requestOptions;
    final unauthorized = err.response?.statusCode == 401;
    if (!unauthorized || _isAuthRoute(options) || options.extra[_retriedKey] == true) {
      handler.next(err);
      return;
    }
    final sent = options.headers['Authorization'];
    final current = await _store.read();
    if (current == null) {
      handler.next(err);
      return;
    }
    // Si otra petición ya refrescó, basta con reintentar con el token nuevo.
    final tokens = sent == 'Bearer ${current.access}' ? await _refreshOnce(current) : current;
    if (tokens == null) {
      handler.next(err);
      return;
    }
    try {
      handler.resolve(await _retry(_retryOptions(options, tokens)));
    } on DioException catch (retryError) {
      handler.next(retryError);
    }
  }

  /// Copia de la petición con el token nuevo; la original no se modifica.
  static RequestOptions _retryOptions(RequestOptions options, AuthTokens tokens) {
    final data = options.data;
    return options.copyWith(
      // Un FormData ya enviado no se puede volver a leer (fotos del reporte).
      data: data is FormData ? data.clone() : data,
      headers: {...options.headers, 'Authorization': 'Bearer ${tokens.access}'},
      extra: {...options.extra, _retriedKey: true},
    );
  }

  Future<AuthTokens?> _refreshOnce(AuthTokens current) {
    return _refreshing ??= _doRefresh(current).whenComplete(() => _refreshing = null);
  }

  Future<AuthTokens?> _doRefresh(AuthTokens current) async {
    try {
      final tokens = await _refresh(current.refresh);
      await _store.write(tokens);
      return tokens;
    } on Object {
      await _store.clear();
      _onSessionExpired();
      return null;
    }
  }
}
