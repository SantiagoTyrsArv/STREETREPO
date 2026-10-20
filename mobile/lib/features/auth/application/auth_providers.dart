import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/config/app_config.dart';
import '../../../core/network/api_client.dart';
import '../data/auth_api.dart';
import '../data/http_auth_repository.dart';
import '../data/secure_token_store.dart';
import '../data/token_store.dart';
import '../domain/auth_repository.dart';

final tokenStoreProvider = Provider<TokenStore>((ref) => SecureTokenStore());

/// Aviso de que el refresco falló y la sesión terminó. Es una señal aparte para no crear
/// el ciclo cliente HTTP → sesión → repositorio → cliente HTTP; la sesión la escucha.
final sessionExpiredSignalProvider = Provider<StreamController<void>>((ref) {
  final signal = StreamController<void>.broadcast(sync: true);
  ref.onDispose(signal.close);
  return signal;
});

/// Cliente HTTP compartido por todas las funcionalidades. Lo arma la sesión porque el
/// refresco y el aviso de sesión terminada son suyos.
final apiClientProvider = Provider<Dio>((ref) {
  late final AuthApi refresher;
  final dio = buildApiClient(
    ref.watch(appConfigProvider),
    ref.watch(tokenStoreProvider),
    (refreshToken) => refresher.refresh(refreshToken),
    () => ref.read(sessionExpiredSignalProvider).add(null),
  );
  // Las rutas /auth/* no pasan por el refresco, así que puede usar el mismo cliente.
  refresher = AuthApi(dio);
  ref.onDispose(dio.close);
  return dio;
});

final authApiProvider = Provider<AuthApi>((ref) => AuthApi(ref.watch(apiClientProvider)));

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => HttpAuthRepository(ref.watch(authApiProvider), ref.watch(tokenStoreProvider)),
);
