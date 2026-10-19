import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/widgets/primary_button.dart';
import 'package:street_repo/core/widgets/state_views.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  testWidgets('ErrorView reintenta', (tester) async {
    var retries = 0;
    await tester.pumpWidget(
      _wrap(ErrorView(message: 'No pudimos cargar', onRetry: () => retries++)),
    );

    await tester.tap(find.text('Reintentar'));

    expect(find.text('No pudimos cargar'), findsOneWidget);
    expect(retries, 1);
  });

  testWidgets('PrimaryButton en carga no responde', (tester) async {
    var presses = 0;
    await tester.pumpWidget(
      _wrap(PrimaryButton(label: 'Enviar', loading: true, onPressed: () => presses++)),
    );

    await tester.tap(find.byType(PrimaryButton));

    expect(presses, 0);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('PrimaryButton tiene al menos 44 px de alto', (tester) async {
    await tester.pumpWidget(_wrap(PrimaryButton(label: 'Enviar', onPressed: () {})));

    expect(tester.getSize(find.byType(PrimaryButton)).height, greaterThanOrEqualTo(44));
  });

  testWidgets('EmptyView muestra título, mensaje y acción', (tester) async {
    await tester.pumpWidget(
      _wrap(
        EmptyView(
          title: 'Aún no tienes reportes',
          message: 'Cuando reportes un daño aparecerá aquí.',
          action: TextButton(onPressed: () {}, child: const Text('Reportar un daño')),
        ),
      ),
    );

    expect(find.text('Aún no tienes reportes'), findsOneWidget);
    expect(find.text('Reportar un daño'), findsOneWidget);
  });
}
