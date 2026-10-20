import 'package:flutter/painting.dart';

/// Tokens visuales de la guía 10.1 y del Figma. Ningún color se escribe fuera de aquí.
abstract final class AppTokens {
  // Base.
  static const Color ink = Color(0xFF1B2430);
  static const Color paper = Color(0xFFF5F3EE);
  static const Color amber = Color(0xFFF5B800);
  static const Color line = Color(0xFFE2DED5);
  static const Color textSecondary = Color(0xFF5B6573);
  static const Color surface = Color(0xFFFFFFFF);

  // Del Figma: filtros sin seleccionar, fondo de la miniatura y textos sobre fondo oscuro.
  static const Color sand = Color(0xFFE8E4DA);
  static const Color thumbnail = Color(0xFFCFC8B8);
  static const Color darkBorder = Color(0xFF4A5565);
  static const Color onDark = Color(0xFFF5F3EE);
  static const Color onDarkMuted = Color(0xFFC9CED6);
  static const Color onDarkSoft = Color(0xFFE4E7EC);

  // Del Figma de acceso: borde de los campos, texto de tarjetas, enlaces, fondo del escudo
  // y el aviso de error.
  static const Color inputBorder = Color(0xFFC9C4B8);
  static const Color cardText = Color(0xFF3D4756);
  static const Color link = Color(0xFF2B6CB0);
  static const Color amberSoft = Color(0xFFFDF0C4);
  static const Color errorSurface = Color(0xFFFDECEA);
  static const Color errorAccent = Color(0xFFB3261E);

  // Del Figma del nuevo reporte: pista de la barra de pasos y fondo de la foto sin tomar.
  static const Color progressTrack = Color(0xFFD8D4CA);
  static const Color photoPlaceholder = Color(0xFF3A4452);

  // Del Figma del paso 2 y de los errores: opción sin elegir, su texto y el suelo del mapa.
  static const Color optionSurface = Color(0xFFF0EDE5);
  static const Color optionText = Color(0xFF4A5565);
  static const Color mapGround = Color(0xFFECEFE9);

  // Estados del reporte: color principal y chip (fondo / texto).
  static const Color registeredFg = Color(0xFF5B6573);
  static const Color registeredChip = Color(0xFFE8EAEE);
  static const Color registeredChipText = Color(0xFF3D4756);
  static const Color evaluatedFg = Color(0xFF2B6CB0);
  static const Color evaluatedChip = Color(0xFFD9E8F7);
  static const Color evaluatedChipText = Color(0xFF1C4E80);
  static const Color prioritizedFg = Color(0xFFB7791F);
  static const Color prioritizedChip = Color(0xFFFDF0C4);
  static const Color prioritizedChipText = Color(0xFF7A4E00);
  static const Color repairedFg = Color(0xFF1F7A5C);
  static const Color repairedChip = Color(0xFFDDF1E8);
  static const Color repairedChipText = Color(0xFF14573F);

  // Severidad.
  static const Color severityLow = Color(0xFF2B6CB0);
  static const Color severityMedium = Color(0xFFB45F06);
  static const Color severityHigh = Color(0xFFB42318);

  // Medidas.
  static const double minTouchTarget = 44;
  static const double buttonHeight = 54;
  static const double buttonRadius = 14;
  static const double cardRadius = 16;
  static const double fieldHeight = 52;
  static const double fieldRadius = 12;
  static const double chipRadius = 10;
  static const double pillHeight = 40;
  static const double screenPadding = 20;

  static const String titleFont = 'Archivo';
  static const String bodyFont = 'Manrope';
}
