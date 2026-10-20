import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/auth_repository.dart';
import 'package:street_repo/features/auth/domain/session.dart';

import 'memory_token_store.dart';

const testUser = UserProfile(id: 'u1', name: 'Ana', email: 'ana@correo.co', role: 'ciudadano');

/// Repositorio falso: cada operación hace lo que se le indique y registra las llamadas.
class FakeAuthRepository implements AuthRepository {
  FakeAuthRepository(this.store);

  final MemoryTokenStore store;
  final List<String> calls = [];
  Future<UserProfile> Function() onMe = () async => testUser;
  Future<PrivacyPolicy> Function() onPrivacyPolicy = () async =>
      const PrivacyPolicy(version: '1.0');
  ApiFailure? registerFailure;
  ApiFailure? loginFailure;
  ApiFailure? logoutFailure;
  String? registeredPolicyVersion;
  String? loggedInEmail;

  @override
  Future<PrivacyPolicy> privacyPolicy() {
    calls.add('privacyPolicy');
    return onPrivacyPolicy();
  }

  @override
  Future<void> register({
    required String name,
    required String email,
    required String password,
    required String policyVersion,
  }) async {
    calls.add('register');
    if (registerFailure != null) throw registerFailure!;
    registeredPolicyVersion = policyVersion;
  }

  @override
  Future<void> login({required String email, required String password}) async {
    calls.add('login');
    if (loginFailure != null) throw loginFailure!;
    loggedInEmail = email;
    await store.write(const AuthTokens(access: 'a', refresh: 'r'));
  }

  @override
  Future<void> logout() async {
    calls.add('logout');
    await store.clear();
    if (logoutFailure != null) throw logoutFailure!;
  }

  @override
  Future<UserProfile> me() {
    calls.add('me');
    return onMe();
  }
}
