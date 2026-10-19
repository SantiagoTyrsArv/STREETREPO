import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/core/widgets/severity_chip.dart';
import 'package:street_repo/core/widgets/status_chip.dart';

Widget _wrap(Widget child) => MaterialApp(
  home: Scaffold(body: Center(child: child)),
);

void main() {
  testWidgets('el chip de estado lleva texto y etiqueta accesible', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(_wrap(const StatusChip(ReportStatus.prioritized)));

    expect(find.text('Priorizado'), findsOneWidget);
    expect(find.bySemanticsLabel('Estado: Priorizado'), findsOneWidget);
    handle.dispose();
  });

  testWidgets('el chip de severidad lleva texto', (tester) async {
    final handle = tester.ensureSemantics();
    await tester.pumpWidget(_wrap(const SeverityChip(Severity.high)));

    expect(find.text('Alta'), findsOneWidget);
    expect(find.bySemanticsLabel('Severidad: Alta'), findsOneWidget);
    handle.dispose();
  });
}
