import 'dart:async';

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
import 'package:street_repo/features/auth/domain/session.dart';
import 'package:street_repo/features/my_reports/application/my_reports_controller.dart';
import 'package:street_repo/features/my_reports/domain/report_detail.dart';

import '../../../support/fake_auth_repository.dart';
import '../../../support/fake_my_reports_repository.dart';
import '../../../support/load_fonts.dart';
import '../../../support/memory_token_store.dart';

void main() {
  late FakeMyReportsRepository repository;
  late FakeAuthRepository auth;

  setUpAll(loadAppFonts);

  setUp(() {
    repository = FakeMyReportsRepository();
    final store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store)
      ..onMe = () async => UserProfile(
        id: 'u1',
        name: 'Ana Ortega',
        email: 'ana@correo.co',
        role: 'ciudadano',
        policyVersion: '1.0',
        policyAcceptedAt: DateTime.utc(2026, 10, 10, 15),
      );
  });

  /// La app con un ciudadano en sesión: arranca en «Mis reportes».
  Future<void> pumpApp(WidgetTester tester, {double textScale = 1}) async {
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
          myReportsRepositoryProvider.overrideWithValue(repository),
        ],
        child: const StreetRepoApp(),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> tapVisible(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  Future<void> openDetail(WidgetTester tester, String id) async {
    unawaited(GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/reportes/$id'));
    await tester.pumpAndSettle();
  }

  group('Mis reportes', () {
    testWidgets('sin reportes muestra el vacío del Figma con «Reportar un daño»', (tester) async {
      await pumpApp(tester);

      expect(find.text('Aún no has reportado daños'), findsOneWidget);
      await tapVisible(tester, find.widgetWithText(FilledButton, 'Reportar un daño'));
      expect(
        GoRouter.of(tester.element(find.byType(Scaffold).last)).state.matchedLocation,
        AppRoutes.newReport,
      );
    });

    testWidgets('sin red muestra el error y «Reintentar» vuelve a cargar', (tester) async {
      repository.beforePage = () async => throw const NetworkFailure();
      await pumpApp(tester);

      expect(find.text('No pudimos cargar tus reportes'), findsOneWidget);

      repository
        ..beforePage = null
        ..reports = [ownReport()];
      await tapVisible(tester, find.widgetWithText(FilledButton, 'Reintentar'));

      expect(find.text('Bache profundo frente al colegio'), findsOneWidget);
    });

    testWidgets('el confirmado dice «Lo confirmaste» y no pide miniatura', (tester) async {
      repository.reports = [ownReport(), confirmedReport()];
      await pumpApp(tester);

      expect(find.text('Lo confirmaste'), findsOneWidget);
      expect(find.text('Calle 18'), findsOneWidget);
      expect(repository.thumbnailRequests, ['own-1']);
      expect(find.bySemanticsLabel('Foto del daño'), findsOneWidget);
    });

    testWidgets('los filtros muestran solo lo que corresponde', (tester) async {
      repository.reports = [
        ownReport(id: 'a', description: 'Reparado ya', status: ReportStatus.repaired),
        ownReport(id: 'b', description: 'Sigue abierto'),
      ];
      await pumpApp(tester);

      await tapVisible(tester, find.bySemanticsLabel('Filtro Reparados'));

      expect(find.text('Reparado ya'), findsOneWidget);
      expect(find.text('Sigue abierto'), findsNothing);
    });

    testWidgets('la barra inferior lleva al perfil', (tester) async {
      await pumpApp(tester);

      await tapVisible(tester, find.bySemanticsLabel('Perfil'));

      expect(find.text('Ana Ortega'), findsOneWidget);
    });
  });

  group('Detalle', () {
    final history = [
      HistoryEntry(status: ReportStatus.registered, changedAt: DateTime.utc(2026, 10, 12, 15)),
      HistoryEntry(status: ReportStatus.evaluated, changedAt: DateTime.utc(2026, 10, 13, 15)),
      HistoryEntry(
        status: ReportStatus.prioritized,
        changedAt: DateTime.utc(2026, 10, 14, 15),
        note: 'Programado para esta semana',
      ),
    ];

    testWidgets('el propio muestra foto, urgencia con coma, «Revisar vía» e historial', (
      tester,
    ) async {
      repository.details['own-1'] = ReportDetail(
        relation: ReportRelation.own,
        report: ownReport(needsRoadReview: true),
        history: history,
      );
      await pumpApp(tester);
      await openDetail(tester, 'own-1');

      expect(find.text('8,70'), findsOneWidget);
      expect(find.text('Revisar vía'), findsOneWidget);
      expect(find.bySemanticsLabel('Foto del daño'), findsOneWidget);
      expect(
        find.bySemanticsLabel('Priorizado. 14 oct · Programado para esta semana'),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel('Registrado. 12 oct · tú enviaste este reporte'),
        findsOneWidget,
      );
      expect(find.bySemanticsLabel('Reparado. Pendiente'), findsOneWidget);
      expect(find.text('4 vecinos confirmaron este daño'), findsOneWidget);
    });

    testWidgets('el confirmado no muestra foto, urgencia ni observaciones', (tester) async {
      repository.details['conf-1'] = ReportDetail(
        relation: ReportRelation.confirmed,
        report: confirmedReport(),
        history: [
          HistoryEntry(status: ReportStatus.registered, changedAt: DateTime.utc(2026, 10, 10)),
        ],
      );
      await pumpApp(tester);
      await openDetail(tester, 'conf-1');

      expect(find.text('Solo quien lo reportó ve la foto'), findsOneWidget);
      expect(find.bySemanticsLabel(RegExp('^Urgencia')), findsNothing);
      expect(find.textContaining('tú enviaste'), findsNothing);
      expect(find.textContaining('Lo confirmaste el 19 oct'), findsOneWidget);
    });
  });

  group('Perfil', () {
    testWidgets('muestra la política aceptada y la abre de solo lectura', (tester) async {
      await pumpApp(tester);
      await tapVisible(tester, find.bySemanticsLabel('Perfil'));

      expect(find.text('Versión 1.0 · aceptada el 10 oct 2026'), findsOneWidget);
      await tapVisible(tester, find.text('Política de tratamiento de datos'));

      expect(find.text('Tu información, con tu permiso'), findsOneWidget);
      expect(find.text('Aceptar y continuar'), findsNothing);
    });

    testWidgets('«Cerrar sesión» cierra la sesión y vuelve a la Bienvenida', (tester) async {
      await pumpApp(tester);
      await tapVisible(tester, find.bySemanticsLabel('Perfil'));

      await tapVisible(tester, find.widgetWithText(FilledButton, 'Cerrar sesión'));

      expect(auth.calls, contains('logout'));
      expect(
        GoRouter.of(tester.element(find.byType(Scaffold).last)).state.matchedLocation,
        AppRoutes.welcome,
      );
    });
  });

  group('texto del sistema al doble (Review Focus 4)', () {
    testWidgets('Mis reportes', (tester) async {
      repository.reports = [ownReport(), confirmedReport()];
      await pumpApp(tester, textScale: 2);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Detalle', (tester) async {
      repository.details['own-1'] = ReportDetail(
        relation: ReportRelation.own,
        report: ownReport(needsRoadReview: true),
        history: [
          HistoryEntry(status: ReportStatus.registered, changedAt: DateTime.utc(2026, 10, 12)),
        ],
      );
      await pumpApp(tester, textScale: 2);
      await openDetail(tester, 'own-1');
      expect(tester.takeException(), isNull);
    });
  });
}
