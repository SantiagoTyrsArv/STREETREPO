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

  test('el mapa usa las teselas de OpenStreetMap si no se configura otro proveedor', () {
    expect(AppConfig.parse('http://api.test').tileUrlTemplate, AppConfig.defaultTileUrl);
  });

  test('el proveedor de teselas se puede cambiar', () {
    final config = AppConfig.parse(
      'http://api.test',
      tileUrl: 'https://teselas.test/{z}/{x}/{y}.png',
    );

    expect(config.tileUrlTemplate, 'https://teselas.test/{z}/{x}/{y}.png');
  });

  test('una plantilla de teselas sin https o sin {z} no arranca', () {
    expect(
      () => AppConfig.parse('http://api.test', tileUrl: 'http://teselas.test/{z}/{x}/{y}.png'),
      throwsStateError,
    );
    expect(
      () => AppConfig.parse('http://api.test', tileUrl: 'https://teselas.test/mapa.png'),
      throwsStateError,
    );
  });
}
