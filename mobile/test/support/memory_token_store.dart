import 'package:street_repo/features/auth/data/token_store.dart';

class MemoryTokenStore implements TokenStore {
  MemoryTokenStore([this._tokens]);

  AuthTokens? _tokens;
  int clears = 0;

  @override
  Future<AuthTokens?> read() async => _tokens;

  @override
  Future<void> write(AuthTokens tokens) async => _tokens = tokens;

  @override
  Future<void> clear() async {
    clears++;
    _tokens = null;
  }
}
