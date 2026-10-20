import 'package:flutter/services.dart';

/// Carga Archivo y Manrope (las de `pubspec.yaml`) para que las pruebas de widgets midan el
/// texto como en el celular; sin esto se usa Ahem, mucho más ancha.
Future<void> loadAppFonts() async {
  final archivo = FontLoader('Archivo')
    ..addFont(rootBundle.load('assets/fonts/Archivo-700.ttf'))
    ..addFont(rootBundle.load('assets/fonts/Archivo-800.ttf'));
  final manrope = FontLoader('Manrope');
  for (final weight in [400, 500, 600, 700]) {
    manrope.addFont(rootBundle.load('assets/fonts/Manrope-$weight.ttf'));
  }
  await Future.wait([archivo.load(), manrope.load()]);
}
