import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:street_repo/app.dart';
import 'package:street_repo/core/routing/app_router.dart';
import 'package:street_repo/core/platform/url_opener.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/my_reports/application/my_reports_controller.dart';
import 'package:street_repo/features/report_new/application/report_draft_controller.dart';
import 'package:street_repo/features/report_new/domain/device_services.dart';

import '../../../support/fake_auth_repository.dart';
import '../../../support/fake_device_services.dart';
import '../../../support/fake_my_reports_repository.dart';
import '../../../support/load_fonts.dart';
import '../../../support/memory_token_store.dart';

void main() {
  late FakeLocationService location;
  late FakePhotoService photos;

  setUpAll(loadAppFonts);

  setUp(() {
    location = FakeLocationService();
    photos = FakePhotoService();
  });

  /// La app con un ciudadano en sesión, abierta en el paso 1 del nuevo reporte.
  Future<void> openStep1(WidgetTester tester, {double textScale = 1}) async {
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
          locationServiceProvider.overrideWithValue(location),
          photoServiceProvider.overrideWithValue(photos),
        ],
        child: const StreetRepoApp(),
      ),
    );
    await tester.pumpAndSettle();
    unawaited(GoRouter.of(tester.element(find.byType(Scaffold).first)).push(AppRoutes.newReport));
    await tester.pumpAndSettle();
  }

  FilledButton continueButton(WidgetTester tester) =>
      tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Continuar'));

  Future<void> tapVisible(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  testWidgets('GPS de ±72 m: explica, ofrece reintentar y no deja continuar (Review Focus 3)', (
    tester,
  ) async {
    location.fixes = [fixWithAccuracy(72)];
    await openStep1(tester);
    await tapVisible(tester, find.bySemanticsLabel('Tomar la foto del daño'));

    expect(
      find.text(
        'La ubicación aún no es precisa (±72 m). Espera unos segundos o sal a un lugar '
        'abierto.',
      ),
      findsOneWidget,
    );
    expect(continueButton(tester).onPressed, isNull);

    location.fixes = [fixWithAccuracy(12)];
    await tapVisible(tester, find.widgetWithText(FilledButton, 'Reintentar'));

    expect(find.text('Precisión GPS ±12 m'), findsOneWidget);
    expect(continueButton(tester).onPressed, isNotNull);
  });

  testWidgets('con ubicación pero sin foto no deja continuar', (tester) async {
    await openStep1(tester);

    expect(find.text('Precisión GPS ±12 m'), findsOneWidget);
    expect(continueButton(tester).onPressed, isNull);
  });

  testWidgets('cancelar la cámara conserva la foto anterior', (tester) async {
    await openStep1(tester);
    await tapVisible(tester, find.bySemanticsLabel('Tomar la foto del daño'));
    expect(find.text('JPG · 0,6 MB'), findsOneWidget);

    photos.nextPhoto = null;
    await tapVisible(tester, find.bySemanticsLabel('Repetir la foto'));

    expect(find.text('JPG · 0,6 MB'), findsOneWidget);
    expect(continueButton(tester).onPressed, isNotNull);
  });

  testWidgets('con el GPS apagado lleva a «Sin acceso a la ubicación»', (tester) async {
    location.state = LocationPermissionState.serviceDisabled;
    await openStep1(tester);

    expect(find.text('Sin acceso a la ubicación'), findsOneWidget);

    await tapVisible(tester, find.widgetWithText(FilledButton, 'Abrir ajustes'));
    expect(location.openedSettings, [LocationPermissionState.serviceDisabled]);
  });

  testWidgets('sin permiso todavía explica los permisos antes de pedirlos', (tester) async {
    location.state = LocationPermissionState.denied;
    await openStep1(tester);

    expect(find.text('Antes de reportar'), findsOneWidget);

    await tapVisible(tester, find.widgetWithText(FilledButton, 'Permitir cámara y ubicación'));
    expect(find.text('Foto y ubicación del daño'), findsOneWidget);
  });

  testWidgets('con el texto del sistema al doble no se desborda (Review Focus 4)', (tester) async {
    location.fixes = [fixWithAccuracy(72)];
    await openStep1(tester, textScale: 2);
    await tapVisible(tester, find.bySemanticsLabel('Tomar la foto del daño'));

    expect(tester.takeException(), isNull);
    await tester.ensureVisible(find.widgetWithText(FilledButton, 'Continuar'));
  });
}
