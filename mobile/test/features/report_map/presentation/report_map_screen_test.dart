import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:street_repo/app.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/core/platform/url_opener.dart';
import 'package:street_repo/core/routing/app_router.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/my_reports/application/my_reports_controller.dart';
import 'package:street_repo/features/my_reports/domain/report_detail.dart';
import 'package:street_repo/features/report_map/application/report_map_controller.dart';
import 'package:street_repo/features/report_map/presentation/report_map_screen.dart';
import 'package:street_repo/features/report_new/application/report_draft_controller.dart';
import 'package:street_repo/features/report_new/application/submit_report_controller.dart';

import '../../../support/fake_auth_repository.dart';
import '../../../support/fake_device_services.dart';
import '../../../support/fake_my_reports_repository.dart';
import '../../../support/fake_new_report_repository.dart';
import '../../../support/fake_report_map_repository.dart';
import '../../../support/load_fonts.dart';
import '../../../support/memory_token_store.dart';

void main() {
  late FakeReportMapRepository map;
  late FakeNewReportRepository reports;
  late FakeMyReportsRepository mine;
  late FakeAuthRepository auth;

  setUpAll(loadAppFonts);

  setUp(() {
    map = FakeReportMapRepository();
    reports = FakeNewReportRepository();
    mine = FakeMyReportsRepository();
    auth = FakeAuthRepository(MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r')));
  });

  /// La app con un ciudadano en sesión, ya en la pestaña Mapa. Las teselas se sustituyen
  /// por una capa vacía: las pruebas no tienen red.
  Future<void> pumpMap(WidgetTester tester, {double textScale = 1}) async {
    tester.view
      ..physicalSize = const Size(390 * 3, 844 * 3)
      ..devicePixelRatio = 3;
    tester.platformDispatcher.textScaleFactorTestValue = textScale;
    addTearDown(tester.view.reset);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStoreProvider.overrideWithValue(auth.store),
          authRepositoryProvider.overrideWithValue(auth),
          urlOpenerProvider.overrideWithValue((_) async => true),
          myReportsRepositoryProvider.overrideWithValue(mine),
          newReportRepositoryProvider.overrideWithValue(reports),
          reportMapRepositoryProvider.overrideWithValue(map),
          locationServiceProvider.overrideWithValue(FakeLocationService()),
          mapTileLayerProvider.overrideWithValue(const SizedBox.shrink()),
        ],
        child: const StreetRepoApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel('Mapa'));
    await tester.pumpAndSettle();
  }

  Future<void> tapVisible(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  Finder pin(String label) => find.bySemanticsLabel(label);

  String location(WidgetTester tester) =>
      GoRouter.of(tester.element(find.byType(Scaffold).last)).state.matchedLocation;

  testWidgets('abre en Pasto, pide el área visible y pinta un marcador por reporte', (
    tester,
  ) async {
    map.reports = [
      mapReport(),
      mapReport(
        id: 'm2',
        status: ReportStatus.evaluated,
        address: 'Calle 18',
        latitude: 1.2146,
        longitude: -77.2805,
      ),
    ];

    await pumpMap(tester);

    expect(find.text('Mapa de reportes'), findsOneWidget);
    final area = map.calls.single.area;
    expect(area.west < -77.2811 && -77.2811 < area.east, isTrue);
    expect(area.south < 1.2136 && 1.2136 < area.north, isTrue);
    expect(pin('Reporte Priorizado en Av. Los Estudiantes'), findsOneWidget);
    expect(pin('Reporte Evaluado en Calle 18'), findsOneWidget);
    // Atribución obligatoria de OpenStreetMap.
    expect(find.textContaining('OpenStreetMap'), findsOneWidget);
  });

  testWidgets('tocar un marcador ajeno abre su ficha con «Confirmar este daño»', (tester) async {
    map.reports = [mapReport()];
    await pumpMap(tester);

    await tester.tap(pin('Reporte Priorizado en Av. Los Estudiantes'));
    await tester.pumpAndSettle();

    expect(find.text('Av. Los Estudiantes'), findsOneWidget);
    expect(find.text('4 vecinos confirmaron este daño'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Confirmar este daño'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Ver detalle'), findsNothing);
  });

  testWidgets('confirmar desde la ficha registra la confirmación y deja ver el detalle', (
    tester,
  ) async {
    map.reports = [mapReport()];
    reports.onConfirm = [() async => 5];
    await pumpMap(tester);
    await tester.tap(pin('Reporte Priorizado en Av. Los Estudiantes'));
    await tester.pumpAndSettle();

    await tapVisible(tester, find.widgetWithText(FilledButton, 'Confirmar este daño'));

    expect(reports.confirmCalls, ['m1']);
    expect(find.text('Confirmación registrada.'), findsOneWidget);
    expect(find.text('Lo confirmaste · 5 vecinos confirmaron este daño'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Confirmar este daño'), findsNothing);
    expect(find.widgetWithText(FilledButton, 'Ver detalle'), findsOneWidget);
  });

  testWidgets('si el servidor rechaza la confirmación, la ficha muestra el motivo', (tester) async {
    map.reports = [mapReport()];
    reports.onConfirm = [
      () async => throw const ApiError(
        status: 409,
        code: 'REPORT_NOT_ACTIVE',
        message: 'Este reporte ya fue reparado.',
      ),
    ];
    await pumpMap(tester);
    await tester.tap(pin('Reporte Priorizado en Av. Los Estudiantes'));
    await tester.pumpAndSettle();

    await tapVisible(tester, find.widgetWithText(FilledButton, 'Confirmar este daño'));

    expect(find.text('Este reporte ya fue reparado.'), findsOneWidget);
  });

  testWidgets('el reporte propio dice «Tu reporte» y abre su detalle', (tester) async {
    map.reports = [mapReport(id: 'own-1', isMine: true)];
    mine.details['own-1'] = ReportDetail(
      relation: ReportRelation.own,
      report: ownReport(),
      history: [
        HistoryEntry(status: ReportStatus.registered, changedAt: DateTime.utc(2026, 10, 12)),
      ],
    );
    await pumpMap(tester);
    await tester.tap(pin('Reporte Priorizado en Av. Los Estudiantes'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Tu reporte'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Confirmar este daño'), findsNothing);
    await tapVisible(tester, find.widgetWithText(FilledButton, 'Ver detalle'));

    expect(location(tester), AppRoutes.reportDetailOf('own-1'));
  });

  testWidgets('un reporte reparado ajeno no se puede confirmar ni abrir', (tester) async {
    map.reports = [mapReport(status: ReportStatus.repaired)];
    await pumpMap(tester);

    await tester.tap(pin('Reporte Reparado en Av. Los Estudiantes'));
    await tester.pumpAndSettle();

    expect(find.text('Av. Los Estudiantes'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Confirmar este daño'), findsNothing);
    expect(find.widgetWithText(FilledButton, 'Ver detalle'), findsNothing);
  });

  testWidgets('«Cerrar ficha» la quita', (tester) async {
    map.reports = [mapReport()];
    await pumpMap(tester);
    await tester.tap(pin('Reporte Priorizado en Av. Los Estudiantes'));
    await tester.pumpAndSettle();

    await tester.tap(find.bySemanticsLabel('Cerrar ficha'));
    await tester.pumpAndSettle();

    expect(find.text('Av. Los Estudiantes'), findsNothing);
  });

  testWidgets('el filtro por estado vuelve a pedir el área con ese estado', (tester) async {
    map.reports = [mapReport(), mapReport(id: 'm2', status: ReportStatus.repaired)];
    await pumpMap(tester);

    await tapVisible(tester, find.bySemanticsLabel('Filtro Reparado'));

    expect(map.calls.last.status, ReportStatus.repaired);
    expect(pin('Reporte Reparado en Av. Los Estudiantes'), findsOneWidget);
    expect(pin('Reporte Priorizado en Av. Los Estudiantes'), findsNothing);
  });

  testWidgets('un área sin reportes lo dice', (tester) async {
    await pumpMap(tester);

    expect(find.text('No hay reportes en esta zona'), findsOneWidget);
    expect(find.text('Mueve el mapa para ver otras zonas.'), findsOneWidget);
  });

  testWidgets('avisa cuando hay más reportes de los que caben', (tester) async {
    map
      ..reports = [mapReport()]
      ..truncated = true;

    await pumpMap(tester);

    expect(find.text('Hay más reportes en esta zona'), findsOneWidget);
  });

  testWidgets('sin conexión lo avisa y «Reintentar» vuelve a cargar', (tester) async {
    map.onList = (_, _) async => throw const NetworkFailure();
    await pumpMap(tester);

    expect(find.text('Sin conexión'), findsOneWidget);
    map
      ..onList = null
      ..reports = [mapReport()];
    await tapVisible(tester, find.text('Reintentar'));

    expect(find.text('Sin conexión'), findsNothing);
    expect(pin('Reporte Priorizado en Av. Los Estudiantes'), findsOneWidget);
  });

  testWidgets('el límite de consultas muestra el mensaje del servidor', (tester) async {
    map.onList = (_, _) async => throw const ApiError(
      status: 429,
      code: 'REPORTS_LIST_RATE_LIMITED',
      message: 'Hiciste muchas consultas en poco tiempo. Intenta de nuevo en un momento.',
    );

    await pumpMap(tester);

    expect(find.text('No pudimos cargar los reportes'), findsOneWidget);
    expect(find.textContaining('Hiciste muchas consultas'), findsOneWidget);
  });

  testWidgets('mover el mapa pide el área nueva tras una pausa', (tester) async {
    map.reports = [mapReport()];
    await pumpMap(tester);
    final before = map.calls.length;

    await tester.drag(find.byType(ReportMapScreen), const Offset(-120, 0));
    await tester.pump(const Duration(milliseconds: 200));
    expect(map.calls.length, before, reason: 'aún no pasa la pausa');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();

    expect(map.calls.length, before + 1);
    expect(map.calls.last.area.west, greaterThan(map.calls.first.area.west));
  });

  testWidgets('con el texto del sistema al doble no se desborda', (tester) async {
    map.reports = [mapReport()];
    await pumpMap(tester, textScale: 2);
    expect(tester.takeException(), isNull);

    await tester.tap(pin('Reporte Priorizado en Av. Los Estudiantes'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('Confirmar este daño'), findsOneWidget);
  });
}
