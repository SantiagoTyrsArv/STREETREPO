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

/// Cuenta regresiva del botón: `4:32`.
String formatCountdown(Duration remaining) {
  final seconds = remaining.inSeconds < 0 ? 0 : remaining.inSeconds;
  return '${seconds ~/ 60}:${(seconds % 60).toString().padLeft(2, '0')}';
}

/// Espera en palabras para el aviso: `4 min 32 s`, `2 min`, `45 s`.
String formatWait(Duration remaining) {
  final seconds = remaining.inSeconds < 0 ? 0 : remaining.inSeconds;
  final minutes = seconds ~/ 60;
  final rest = seconds % 60;
  if (minutes == 0) return '$rest s';
  return rest == 0 ? '$minutes min' : '$minutes min $rest s';
}
