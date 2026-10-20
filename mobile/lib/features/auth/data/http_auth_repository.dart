import '../domain/auth_repository.dart';
import '../domain/session.dart';
import 'auth_api.dart';
import 'token_store.dart';

class HttpAuthRepository implements AuthRepository {
  HttpAuthRepository(this._api, this._tokens);

  final AuthApi _api;
  final TokenStore _tokens;

  @override
  Future<PrivacyPolicy> privacyPolicy() => _api.privacyPolicy();

  @override
  Future<void> register({
    required String name,
    required String email,
    required String password,
    required String policyVersion,
  }) => _api.register(name: name, email: email, password: password, policyVersion: policyVersion);

  @override
  Future<void> login({required String email, required String password}) async {
    await _tokens.write(await _api.login(email: email, password: password));
  }

  @override
  Future<void> logout() async {
    final tokens = await _tokens.read();
    try {
      if (tokens != null) await _api.logout(tokens.refresh);
    } finally {
      // Sin red, el servidor no se entera, pero el refresco vence solo; el celular queda limpio.
      await _tokens.clear();
    }
  }

  @override
  Future<UserProfile> me() => _api.me();
}
