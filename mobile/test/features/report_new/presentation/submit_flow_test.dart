import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:street_repo/app.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/core/platform/url_opener.dart';
import 'package:street_repo/core/routing/app_router.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/my_reports/application/my_reports_controller.dart';
import 'package:street_repo/features/report_new/application/report_draft_controller.dart';
import 'package:street_repo/features/report_new/application/submit_report_controller.dart';

import '../../../support/fake_auth_repository.dart';
import '../../../support/fake_device_services.dart';
import '../../../support/fake_my_reports_repository.dart';
import '../../../support/fake_new_report_repository.dart';
import '../../../support/load_fonts.dart';
import '../../../support/memory_token_store.dart';

void main() {
  late FakeNewReportRepository repository;

  setUpAll(loadAppFonts);

  setUp(() => repository = FakeNewReportRepository());

  /// La app con un ciudadano en sesión, el paso 1 completo y abierta en el paso 2.
  Future<void> openStep2(WidgetTester tester, {double textScale = 1}) async {
    tester.view
      ..physicalSize = const Size(390 * 3, 844 * 3)
      ..devicePixelRatio = 3;
    tester.platformDispatcher.textScaleFactorTestValue = textScale;
    addTearDown(tester.view.reset);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    final store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStoreProvider.overrideWithValue(store),
          authRepositoryProvider.overrideWithValue(FakeAuthRepository(store)),
          urlOpenerProvider.overrideWithValue((_) async => true),
          myReportsRepositoryProvider.overrideWithValue(FakeMyReportsRepository()),
          locationServiceProvider.overrideWithValue(FakeLocationService()),
          photoServiceProvider.overrideWithValue(FakePhotoService()),
          newReportRepositoryProvider.overrideWithValue(repository),
          submitRetryWaitProvider.overrideWithValue((_) async {}),
        ],
        child: const StreetRepoApp(),
      ),
    );
    await tester.pumpAndSettle();
    final router = GoRouter.of(tester.element(find.byType(Scaffold).first));
    unawaited(router.push(AppRoutes.newReport));
    await tester.pumpAndSettle();
    final container = ProviderScope.containerOf(tester.element(find.byType(Scaffold).last));
    await container.read(reportDraftProvider.notifier).capturePhoto();
    await container.read(reportDraftProvider.notifier).locate();
    await tester.pumpAndSettle();
    unawaited(router.push(AppRoutes.newReportSeverity));
    await tester.pumpAndSettle();
  }

  FilledButton button(WidgetTester tester, String label) =>
      tester.widget<FilledButton>(find.widgetWithText(FilledButton, label));

  Future<void> tapVisible(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  Future<void> chooseMediumAndSend(WidgetTester tester) async {
    await tapVisible(tester, find.bySemanticsLabel(RegExp('^Severidad media')));
    await tapVisible(tester, find.widgetWithText(FilledButton, 'Enviar reporte'));
  }

  group('paso 2 · severidad', () {
    testWidgets('«Enviar» deshabilitado sin severidad y contador 0/500', (tester) async {
      await openStep2(tester);

      expect(find.text('Paso 2 de 2'), findsOneWidget);
      expect(button(tester, 'Enviar reporte').onPressed, isNull);
      expect(find.text('0/500'), findsOneWidget);

      await tester.enterText(find.byType(TextField), 'Hueco grande');
      await tester.pump();
      expect(find.text('12/500'), findsOneWidget);

      await tapVisible(tester, find.bySemanticsLabel(RegExp('^Severidad alta')));
      expect(button(tester, 'Enviar reporte').onPressed, isNotNull);
    });

    testWidgets('un envío correcto lleva a «Reporte enviado» con estado y dirección', (
      tester,
    ) async {
      await openStep2(tester);
      await chooseMediumAndSend(tester);

      expect(find.text('¡Gracias! Tu reporte quedó registrado'), findsOneWidget);
      expect(find.text('Calle 18'), findsOneWidget);
      expect(find.bySemanticsLabel('Estado actual: Evaluado'), findsOneWidget);
      expect(repository.createCalls.single.draft.description, '');
    });

    testWidgets('sin red tras los reintentos explica y ofrece reintentar', (tester) async {
      repository.onCreate = [() async => throw const NetworkFailure()];
      await openStep2(tester);
      await chooseMediumAndSend(tester);

      expect(find.text(const NetworkFailure().message), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Reintentar el envío'), findsOneWidget);
      expect(find.bySemanticsLabel(RegExp('^Severidad media')), findsOneWidget);
    });

    testWidgets('fuera del área lleva a su pantalla', (tester) async {
      repository.onCreate = [
        () async => throw const ApiError(
          status: 422,
          code: 'LOCATION_OUTSIDE_SERVICE_AREA',
          message: 'Fuera',
        ),
      ];
      await openStep2(tester);
      await chooseMediumAndSend(tester);

      expect(find.text('Este punto está fuera del área de servicio'), findsOneWidget);
    });

    testWidgets('el límite muestra la espera', (tester) async {
      repository.onCreate = [
        () async => throw const ApiError(
          status: 429,
          code: 'REPORT_RATE_LIMITED',
          message: 'Muchos',
          retryAfter: Duration(minutes: 18),
        ),
      ];
      await openStep2(tester);
      await chooseMediumAndSend(tester);

      expect(find.text('Alcanzaste el límite de reportes'), findsOneWidget);
      expect(find.text('18 min'), findsOneWidget);

      await tapVisible(tester, find.widgetWithText(FilledButton, 'Entendido'));
      expect(find.text('¿Qué tan grave es el daño?'), findsOneWidget);
    });

    testWidgets('la foto rechazada muestra el mensaje del servidor y vuelve al paso 1', (
      tester,
    ) async {
      repository.onCreate = [
        () async => throw const ApiError(
          status: 422,
          code: 'PHOTO_INVALID',
          message: 'No pudimos leer la foto. Toma otra e intenta de nuevo.',
        ),
      ];
      await openStep2(tester);
      await chooseMediumAndSend(tester);

      expect(find.text('No pudimos usar esta foto'), findsOneWidget);
      expect(find.text('No pudimos leer la foto. Toma otra e intenta de nuevo.'), findsOneWidget);

      await tapVisible(tester, find.widgetWithText(FilledButton, 'Tomar otra foto'));
      expect(find.text('Foto y ubicación del daño'), findsOneWidget);
      expect(find.bySemanticsLabel('Tomar la foto del daño'), findsOneWidget);
    });
  });

  group('posible duplicado', () {
    testWidgets('el reporte propio dice «Tu reporte» y no se puede confirmar', (tester) async {
      repository.onNearby = [
        () async => [nearbyReport(isMine: true)],
      ];
      await openStep2(tester);
      await chooseMediumAndSend(tester);

      expect(find.text('Ya existe un reporte cerca'), findsOneWidget);
      expect(find.text('Tu reporte'), findsOneWidget);
      expect(find.text('Es el mismo daño: confirmarlo'), findsNothing);
      expect(find.widgetWithText(FilledButton, 'Es otro daño: enviar mi reporte'), findsOneWidget);
    });

    testWidgets('el ajeno se confirma una sola vez aunque se toque dos veces', (tester) async {
      final reply = Completer<int>();
      repository
        ..onNearby = [
          () async => [nearbyReport()],
        ]
        ..onConfirm = [() => reply.future];
      await openStep2(tester);
      await chooseMediumAndSend(tester);

      expect(
        find.text(
          'Encontramos un reporte activo a 12 m de tu ubicación. '
          'Si es el mismo daño, confírmalo en lugar de crear uno nuevo.',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('3 vecinos lo han confirmado'), findsOneWidget);
      final confirm = find.widgetWithText(FilledButton, 'Es el mismo daño: confirmarlo');
      await tester.ensureVisible(confirm);
      await tester.tap(confirm);
      await tester.pump();
      await tester.tap(find.byType(FilledButton).first, warnIfMissed: false);
      await tester.pump();
      reply.complete(4);
      await tester.pumpAndSettle();

      expect(repository.confirmCalls, ['r1']);
      expect(find.text('Confirmación registrada'), findsOneWidget);
      expect(find.textContaining('ya tiene 4 confirmaciones'), findsOneWidget);
    });

    testWidgets('«Es otro daño» crea el reporte de todos modos', (tester) async {
      repository.onNearby = [
        () async => [nearbyReport()],
      ];
      await openStep2(tester);
      await chooseMediumAndSend(tester);

      await tapVisible(
        tester,
        find.widgetWithText(FilledButton, 'Es otro daño: enviar mi reporte'),
      );

      expect(repository.createCalls.single.createAnyway, isTrue);
      expect(find.text('¡Gracias! Tu reporte quedó registrado'), findsOneWidget);
    });
  });

  group('texto del sistema al doble (Review Focus 4)', () {
    testWidgets('Severidad', (tester) async {
      await openStep2(tester, textScale: 2);
      expect(tester.takeException(), isNull);
      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Enviar reporte'));
    });

    testWidgets('Posible duplicado con dos candidatos', (tester) async {
      repository.onNearby = [
        () async => [nearbyReport(), nearbyReport(id: 'r2', distance: 20, isMine: true)],
      ];
      await openStep2(tester, textScale: 2);
      await chooseMediumAndSend(tester);

      expect(tester.takeException(), isNull);
      expect(find.text('Ya existen reportes cerca'), findsOneWidget);
      await tester.ensureVisible(
        find.widgetWithText(FilledButton, 'Es otro daño: enviar mi reporte'),
      );
    });

    testWidgets('Reporte enviado', (tester) async {
      await openStep2(tester, textScale: 2);
      await chooseMediumAndSend(tester);

      expect(tester.takeException(), isNull);
      await tester.ensureVisible(find.widgetWithText(FilledButton, 'Ir a Mis reportes'));
    });
  });
}
