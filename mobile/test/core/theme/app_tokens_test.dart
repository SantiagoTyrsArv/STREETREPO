import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/theme/app_theme.dart';
import 'package:street_repo/core/theme/app_tokens.dart';

void main() {
  test('colores base de la guía 10.1', () {
    expect(AppTokens.ink, const Color(0xFF1B2430));
    expect(AppTokens.paper, const Color(0xFFF5F3EE));
    expect(AppTokens.amber, const Color(0xFFF5B800));
    expect(AppTokens.line, const Color(0xFFE2DED5));
    expect(AppTokens.textSecondary, const Color(0xFF5B6573));
  });

  test('chips de estado: fondo y texto', () {
    expect(AppTokens.registeredChip, const Color(0xFFE8EAEE));
    expect(AppTokens.registeredChipText, const Color(0xFF3D4756));
    expect(AppTokens.evaluatedChip, const Color(0xFFD9E8F7));
    expect(AppTokens.evaluatedChipText, const Color(0xFF1C4E80));
    expect(AppTokens.prioritizedChip, const Color(0xFFFDF0C4));
    expect(AppTokens.prioritizedChipText, const Color(0xFF7A4E00));
    expect(AppTokens.repairedChip, const Color(0xFFDDF1E8));
    expect(AppTokens.repairedChipText, const Color(0xFF14573F));
  });

  test('severidad', () {
    expect(AppTokens.severityLow, const Color(0xFF2B6CB0));
    expect(AppTokens.severityMedium, const Color(0xFFB45F06));
    expect(AppTokens.severityHigh, const Color(0xFFB42318));
  });

  test('el tema usa papel de fondo, Manrope en el cuerpo y Archivo en títulos', () {
    final theme = buildAppTheme();

    expect(theme.scaffoldBackgroundColor, AppTokens.paper);
    expect(theme.textTheme.bodyMedium?.fontFamily, 'Manrope');
    expect(theme.textTheme.headlineMedium?.fontFamily, 'Archivo');
    expect(theme.textTheme.headlineMedium?.fontWeight, FontWeight.w800);
  });
}
