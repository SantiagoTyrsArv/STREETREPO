import 'package:dio/dio.dart';

import '../../features/auth/data/token_store.dart';
import '../config/app_config.dart';
import 'session_interceptor.dart';

/// Cliente HTTP de la app con la sesión: token en cada petición y refresco ante un 401.
Dio buildApiClient(
  AppConfig config,
  TokenStore store,
  RefreshTokens refresh,
  void Function() onSessionExpired,
) {
  final dio = Dio(
    BaseOptions(
      baseUrl: config.apiUrl('').toString(),
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      // Las fotos pueden tardar en subir con 4G.
      sendTimeout: const Duration(seconds: 60),
    ),
  );
  dio.interceptors.add(
    SessionInterceptor(
      store: store,
      refresh: refresh,
      onSessionExpired: onSessionExpired,
      // El reintento pasa por el mismo cliente; el interceptor lo reconoce y no refresca otra vez.
      retry: dio.fetch<dynamic>,
    ),
  );
  return dio;
}
