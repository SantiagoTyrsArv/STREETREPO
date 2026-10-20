import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:street_repo/features/auth/data/secure_token_store.dart';
import 'package:street_repo/features/auth/data/token_store.dart';

class _MockStorage extends Mock implements FlutterSecureStorage {}

void main() {
  late _MockStorage storage;
  late Map<String, String> values;
  late SecureTokenStore store;

  setUp(() {
    storage = _MockStorage();
    values = {};
    when(() => storage.read(key: any(named: 'key')))
        .thenAnswer((call) async => values[call.namedArguments[#key]]);
    when(
      () => storage.write(
        key: any(named: 'key'),
        value: any(named: 'value'),
      ),
    ).thenAnswer(
      (call) async =>
          values[call.namedArguments[#key] as String] = call.namedArguments[#value] as String,
    );
    when(() => storage.delete(key: any(named: 'key')))
        .thenAnswer((call) async => values.remove(call.namedArguments[#key]));
    store = SecureTokenStore(storage);
  });

  test('guarda los dos tokens en una sola entrada y los lee', () async {
    await store.write(const AuthTokens(access: 'acceso', refresh: 'refresco'));

    expect(values, hasLength(1));
    expect(await store.read(), const AuthTokens(access: 'acceso', refresh: 'refresco'));
  });

  test('sin entrada no hay sesión', () async {
    expect(await store.read(), isNull);
  });

  test('si el Keystore no puede descifrar, borra y trata como sin sesión', () async {
    values['session_tokens'] = 'ilegible';
    when(() => storage.read(key: any(named: 'key')))
        .thenThrow(PlatformException(code: 'Exception', message: 'BadPaddingException'));

    expect(await store.read(), isNull);
    expect(values, isEmpty);
  });

  test('una entrada con otra forma se descarta', () async {
    values['session_tokens'] = '{"access":"solo-acceso"}';

    expect(await store.read(), isNull);
    expect(values, isEmpty);
  });

  test('borrar elimina la sesión', () async {
    await store.write(const AuthTokens(access: 'a', refresh: 'r'));

    await store.clear();

    expect(await store.read(), isNull);
  });
}
