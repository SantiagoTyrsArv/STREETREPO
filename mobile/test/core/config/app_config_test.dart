import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/config/app_config.dart';

void main() {
  test('lee la URL del backend', () {
    final config = AppConfig.parse('http://192.168.1.20:8000');

    expect(config.apiBaseUrl, Uri.parse('http://192.168.1.20:8000'));
    expect(config.apiUrl('/reports'), Uri.parse('http://192.168.1.20:8000/api/v1/reports'));
  });

  test('sin URL no arranca', () {
    expect(() => AppConfig.parse(''), throwsStateError);
  });

  test('una URL sin http(s) no arranca', () {
    expect(() => AppConfig.parse('192.168.1.20:8000'), throwsStateError);
  });
}
