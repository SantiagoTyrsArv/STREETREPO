import 'package:flutter_test/flutter_test.dart';

/// Pautas de accesibilidad de Flutter sobre lo que hay en pantalla (fase 8; guía 10.3):
/// áreas táctiles de al menos 44 × 44 y elementos tocables con etiqueta.
///
/// - Áreas táctiles: la guía fija 44 px (lo que usa el diseño aprobado, y lo que pide iOS);
///   WCAG 2.2 AA (2.5.8) exige 24. La pauta de Android (48 dp) no se aplica: pediría cambiar
///   el diseño aprobado sin que haya incumplimiento de WCAG AA (fila 145 de la bitácora).
/// - Contraste: no se usa `textContrastGuideline`, que mide sobre una captura y confunde el
///   borde de una tarjeta con el texto (falsos positivos de 1,4:1). El contraste se verifica
///   de forma exacta sobre los pares de tokens en `test/core/theme/token_contrast_test.dart`.
Future<void> expectMeetsAccessibilityGuidelines(WidgetTester tester) async {
  final handle = tester.ensureSemantics();
  try {
    await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
    await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
  } finally {
    handle.dispose();
  }
}
