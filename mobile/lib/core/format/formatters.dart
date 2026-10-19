import 'package:intl/intl.dart';

/// Colombia no tiene horario de verano: Bogotá es siempre UTC-5 (guía 9.2).
const Duration _bogotaOffset = Duration(hours: -5);
const String _locale = 'es_CO';

DateTime _inBogota(DateTime utc) => utc.toUtc().add(_bogotaOffset);

DateTime _day(DateTime dateTime) => DateTime.utc(dateTime.year, dateTime.month, dateTime.day);

/// Urgencia y otros decimales con coma (`8,70`); la API usa punto.
String formatScore(num value) => NumberFormat('0.00', _locale).format(value);

/// Fecha corta en hora de Bogotá: `13 oct`.
String formatShortDate(DateTime utc) =>
    DateFormat('d MMM', _locale).format(_inBogota(utc)).replaceAll('.', '');

/// Antigüedad como en el diseño de «Mis reportes»: `hoy`, `hace 3 días`, `hace 1 semana`.
String formatRelative(DateTime utc, DateTime nowUtc) {
  final days = _day(_inBogota(nowUtc)).difference(_day(_inBogota(utc))).inDays;
  if (days <= 0) return 'hoy';
  if (days == 1) return 'ayer';
  if (days < 7) return 'hace $days días';
  if (days < 30) {
    final weeks = days ~/ 7;
    return weeks == 1 ? 'hace 1 semana' : 'hace $weeks semanas';
  }
  return formatShortDate(utc);
}
