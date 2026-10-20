import 'package:flutter/material.dart';

import 'app_tokens.dart';

ThemeData buildAppTheme() {
  const scheme = ColorScheme.light(
    primary: AppTokens.amber,
    onPrimary: AppTokens.ink,
    secondary: AppTokens.ink,
    onSecondary: AppTokens.onDark,
    surface: AppTokens.surface,
    onSurface: AppTokens.ink,
    error: AppTokens.severityHigh,
    outline: AppTokens.line,
  );
  final base = ThemeData(useMaterial3: true, colorScheme: scheme, fontFamily: AppTokens.bodyFont);
  final text = base.textTheme.apply(
    fontFamily: AppTokens.bodyFont,
    bodyColor: AppTokens.ink,
    displayColor: AppTokens.ink,
  );
  TextStyle title(TextStyle? style, double size) => (style ?? const TextStyle()).copyWith(
    fontFamily: AppTokens.titleFont,
    fontWeight: FontWeight.w800,
    fontSize: size,
    color: AppTokens.ink,
  );

  return base.copyWith(
    scaffoldBackgroundColor: AppTokens.paper,
    textTheme: text.copyWith(
      headlineLarge: title(text.headlineLarge, 38),
      headlineMedium: title(text.headlineMedium, 28),
      headlineSmall: title(text.headlineSmall, 22),
      titleLarge: text.titleLarge?.copyWith(fontWeight: FontWeight.w700, fontSize: 18),
      titleMedium: text.titleMedium?.copyWith(fontWeight: FontWeight.w700, fontSize: 15),
      bodyLarge: text.bodyLarge?.copyWith(fontSize: 16),
      bodyMedium: text.bodyMedium?.copyWith(fontSize: 14),
      bodySmall: text.bodySmall?.copyWith(fontSize: 13, color: AppTokens.textSecondary),
      labelLarge: text.labelLarge?.copyWith(fontWeight: FontWeight.w700, fontSize: 16),
      labelSmall: text.labelSmall?.copyWith(fontWeight: FontWeight.w700, fontSize: 12),
    ),
    // Campos del Figma: 52 px de alto, radio 12 y borde de 1,5 px.
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppTokens.surface,
      // El borde outline añade 4 px a cada lado: 12 + 4 = los 16 px del Figma.
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 15),
      border: _fieldBorder(AppTokens.inputBorder),
      enabledBorder: _fieldBorder(AppTokens.inputBorder),
      focusedBorder: _fieldBorder(AppTokens.ink),
      errorBorder: _fieldBorder(AppTokens.errorAccent),
      focusedErrorBorder: _fieldBorder(AppTokens.errorAccent),
    ),
    materialTapTargetSize: MaterialTapTargetSize.padded,
  );
}

OutlineInputBorder _fieldBorder(Color color) => OutlineInputBorder(
  borderRadius: BorderRadius.circular(AppTokens.fieldRadius),
  borderSide: BorderSide(color: color, width: 1.5),
);
