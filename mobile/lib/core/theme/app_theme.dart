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
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppTokens.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppTokens.buttonRadius),
        borderSide: const BorderSide(color: AppTokens.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppTokens.buttonRadius),
        borderSide: const BorderSide(color: AppTokens.line),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppTokens.buttonRadius),
        borderSide: const BorderSide(color: AppTokens.ink, width: 1.5),
      ),
    ),
    materialTapTargetSize: MaterialTapTargetSize.padded,
  );
}
