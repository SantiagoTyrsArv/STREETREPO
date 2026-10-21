import 'package:dio/dio.dart';

import '../../../core/network/api_error.dart';
import '../domain/session.dart';
import 'token_store.dart';

/// Rutas de autenticación y cuenta de la API (`/auth/*`, `/me`, `/privacy-policy`).
/// Traduce los errores a `ApiFailure`; una respuesta con otra forma es `UnexpectedFailure`.
class AuthApi {
  AuthApi(this._dio);

  final Dio _dio;

  Future<PrivacyPolicy> privacyPolicy() => _call(() async {
    final json = _json(await _dio.get<Object?>('/privacy-policy'));
    final url = json['url'];
    return PrivacyPolicy(
      version: _field<String>(json, 'version'),
      url: url is String ? Uri.tryParse(url) : null,
    );
  });

  Future<void> register({
    required String name,
    required String email,
    required String password,
    required String policyVersion,
  }) => _call(() async {
    await _dio.post<Object?>(
      '/auth/register',
      data: {
        'name': name,
        'email': email,
        'password': password,
        // Solo se llega aquí si el ciudadano marcó la casilla de la política.
        'accepted_policy': true,
        'policy_version': policyVersion,
      },
    );
  });

  Future<AuthTokens> login({required String email, required String password}) => _call(
    () async => _tokens(
      await _dio.post<Object?>('/auth/login', data: {'email': email, 'password': password}),
    ),
  );

  Future<AuthTokens> refresh(String refreshToken) => _call(
    () async =>
        _tokens(await _dio.post<Object?>('/auth/refresh', data: {'refresh_token': refreshToken})),
  );

  Future<void> logout(String refreshToken) => _call(() async {
    await _dio.post<Object?>('/auth/logout', data: {'refresh_token': refreshToken});
  });

  Future<UserProfile> me() => _call(() async {
    final json = _json(await _dio.get<Object?>('/me'));
    return UserProfile(
      id: _field<String>(json, 'id'),
      name: _field<String>(json, 'name'),
      email: _field<String>(json, 'email'),
      role: _field<String>(json, 'role'),
      policyVersion: switch (json['policy_version']) {
        final String value => value,
        _ => null,
      },
      policyAcceptedAt: switch (json['policy_accepted_at']) {
        final String value => DateTime.parse(value),
        _ => null,
      },
    );
  });

  static Future<T> _call<T>(Future<T> Function() request) async {
    try {
      return await request();
    } on DioException catch (e) {
      throw ApiFailure.fromDioException(e);
    } on FormatException {
      throw const UnexpectedFailure();
    }
  }

  static AuthTokens _tokens(Response<Object?> response) {
    final json = _json(response);
    return AuthTokens(
      access: _field<String>(json, 'access_token'),
      refresh: _field<String>(json, 'refresh_token'),
    );
  }

  static Map<String, dynamic> _json(Response<Object?> response) {
    final body = response.data;
    if (body is Map<String, dynamic>) return body;
    throw const FormatException('La respuesta no es un objeto JSON');
  }

  static T _field<T>(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is T) return value;
    throw FormatException('Campo inválido: $key');
  }
}
