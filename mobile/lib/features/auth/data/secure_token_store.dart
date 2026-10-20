import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'token_store.dart';

/// Tokens en Keystore/Keychain, nunca en preferencias planas (guía 7.3).
///
/// Los dos tokens van en una sola entrada: escribirlos por separado podría dejar un acceso
/// nuevo con un refresco viejo si la app se cierra a mitad, y el servidor tomaría ese
/// refresco como reutilizado y revocaría la sesión (propuesta 53).
class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  static const _sessionKey = 'session_tokens';

  final FlutterSecureStorage _storage;

  @override
  Future<AuthTokens?> read() async {
    try {
      final raw = await _storage.read(key: _sessionKey);
      if (raw == null) return null;
      final json = jsonDecode(raw);
      if (json case {'access': final String access, 'refresh': final String refresh}) {
        return AuthTokens(access: access, refresh: refresh);
      }
      throw const FormatException('Entrada de sesión con otra forma');
    } on PlatformException {
      // Copia restaurada en otro equipo o Keystore cambiado: no se puede descifrar.
      await _discard();
      return null;
    } on FormatException {
      await _discard();
      return null;
    }
  }

  @override
  Future<void> write(AuthTokens tokens) => _storage.write(
    key: _sessionKey,
    value: jsonEncode({'access': tokens.access, 'refresh': tokens.refresh}),
  );

  @override
  Future<void> clear() => _storage.delete(key: _sessionKey);

  /// Sin sesión legible, la app vuelve a pedir el ingreso en lugar de quedarse atascada.
  Future<void> _discard() async {
    try {
      await clear();
    } on PlatformException {
      // Si tampoco se puede borrar, la próxima escritura la reemplaza.
    }
  }
}
