import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:street_repo/core/format/formatters.dart';

void main() {
  setUpAll(() => initializeDateFormatting('es_CO'));

  group('formatScore', () {
    test('usa coma decimal y dos decimales', () {
      expect(formatScore(8.7), '8,70');
      expect(formatScore(3.6), '3,60');
      expect(formatScore(10), '10,00');
    });
  });

  group('formatShortDate', () {
    test('muestra el día en hora de Bogotá', () {
      // Las 3:00 UTC del 14 son las 22:00 del 13 en Bogotá (UTC-5).
      expect(formatShortDate(DateTime.utc(2026, 10, 14, 3)), '13 oct');
      expect(formatShortDate(DateTime.utc(2026, 1, 5, 12)), '5 ene');
    });
  });

  group('formatRelative', () {
    final now = DateTime.utc(2026, 10, 19, 15);

    test('mismo día en Bogotá es hoy', () {
      expect(formatRelative(DateTime.utc(2026, 10, 19, 6), now), 'hoy');
    });

    test('ayer', () {
      expect(formatRelative(DateTime.utc(2026, 10, 18, 15), now), 'ayer');
    });

    test('días y semanas como en el diseño', () {
      expect(formatRelative(DateTime.utc(2026, 10, 16, 15), now), 'hace 3 días');
      expect(formatRelative(DateTime.utc(2026, 10, 12, 15), now), 'hace 1 semana');
      expect(formatRelative(DateTime.utc(2026, 9, 28, 15), now), 'hace 3 semanas');
    });

    test('más de un mes muestra la fecha corta', () {
      expect(formatRelative(DateTime.utc(2026, 8, 1, 15), now), '1 ago');
    });
  });

  group('cuenta regresiva', () {
    test('formatCountdown usa m:ss como el botón del Figma', () {
      expect(formatCountdown(const Duration(minutes: 4, seconds: 32)), '4:32');
      expect(formatCountdown(const Duration(seconds: 90)), '1:30');
      expect(formatCountdown(const Duration(seconds: 5)), '0:05');
      expect(formatCountdown(const Duration(seconds: -3)), '0:00');
    });

    test('formatWait la dice en palabras', () {
      expect(formatWait(const Duration(minutes: 4, seconds: 32)), '4 min 32 s');
      expect(formatWait(const Duration(minutes: 2)), '2 min');
      expect(formatWait(const Duration(seconds: 45)), '45 s');
    });
  });
}
