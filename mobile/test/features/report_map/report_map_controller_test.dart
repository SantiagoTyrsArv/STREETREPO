import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/my_reports/application/my_reports_controller.dart';
import 'package:street_repo/features/report_map/application/report_map_controller.dart';
import 'package:street_repo/features/report_map/domain/map_report.dart';
import 'package:street_repo/features/report_new/application/report_draft_controller.dart';
import 'package:street_repo/features/report_new/application/submit_report_controller.dart';
import 'package:street_repo/features/report_new/domain/device_services.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/fake_device_services.dart';
import '../../support/fake_my_reports_repository.dart';
import '../../support/fake_new_report_repository.dart';
import '../../support/fake_report_map_repository.dart';
import '../../support/memory_token_store.dart';

const _area = MapArea(west: -77.29, south: 1.2, east: -77.27, north: 1.22);
const _other = MapArea(west: -77.3, south: 1.2, east: -77.28, north: 1.22);

void main() {
  late FakeReportMapRepository map;
  late FakeNewReportRepository reports;
  late FakeMyReportsRepository mine;
  late FakeLocationService location;
  late ProviderContainer c;

  ReportMapController controller() => c.read(reportMapProvider.notifier);
  ReportMapState state() => c.read(reportMapProvider);

  setUp(() async {
    final store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    map = FakeReportMapRepository()..reports = [mapReport()];
    reports = FakeNewReportRepository();
    mine = FakeMyReportsRepository();
    location = FakeLocationService();
    c = ProviderContainer.test(
      overrides: [
        tokenStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(store)),
        reportMapRepositoryProvider.overrideWithValue(map),
        newReportRepositoryProvider.overrideWithValue(reports),
        myReportsRepositoryProvider.overrideWithValue(mine),
        locationServiceProvider.overrideWithValue(location),
      ],
    );
    await c.read(sessionControllerProvider.future);
    c.listen(reportMapProvider, (_, _) {});
  });

  test('al mostrar un área carga sus reportes', () async {
    await controller().showArea(_area);

    expect(map.calls, [(area: _area, status: null)]);
    expect(state().reports.single.id, 'm1');
    expect((state().loading, state().loaded, state().failure), (false, true, null));
  });

  test('la misma área no se vuelve a pedir, salvo que se fuerce', () async {
    await controller().showArea(_area);
    await controller().showArea(_area);
    expect(map.calls, hasLength(1));

    await controller().showArea(_area, force: true);

    expect(map.calls, hasLength(2));
  });

  test('el filtro vuelve a pedir el área con ese estado y cierra la ficha', () async {
    map.reports = [mapReport(), mapReport(id: 'm2', status: ReportStatus.repaired)];
    await controller().showArea(_area);
    controller().select('m1');

    await controller().setFilter(ReportStatus.repaired);

    expect(map.calls.last, (area: _area, status: ReportStatus.repaired));
    expect(state().reports.single.id, 'm2');
    expect(state().selectedId, isNull);
  });

  test('si el reporte elegido sale del área, su ficha se cierra', () async {
    await controller().showArea(_area);
    controller().select('m1');
    expect(state().selected?.id, 'm1');
    map.reports = [mapReport(id: 'otro')];

    await controller().showArea(_other);

    expect(state().selectedId, isNull);
  });

  test('sin red conserva lo último cargado y avisa el fallo', () async {
    await controller().showArea(_area);
    map.onList = (_, _) async => throw const NetworkFailure();

    await controller().showArea(_other);

    expect(state().failure, isA<NetworkFailure>());
    expect(state().reports.single.id, 'm1');
    expect(state().loading, isFalse);
  });

  test('tras un fallo, reintentar vuelve a pedir la misma área', () async {
    map.onList = (_, _) async => throw const NetworkFailure();
    await controller().showArea(_area);
    expect(state().loaded, isFalse);
    map.onList = null;

    await controller().reload();

    expect(map.calls.last.area, _area);
    expect((state().failure, state().loaded), (null, true));
  });

  test('una respuesta que llega tarde no pisa la de un área más nueva', () async {
    final slow = Completer<MapReportsPage>();
    map.onList = (area, _) => area == _area
        ? slow.future
        : Future.value(MapReportsPage(items: [mapReport(id: 'nuevo')], truncated: false));

    final first = controller().showArea(_area);
    await controller().showArea(_other);
    slow.complete(MapReportsPage(items: [mapReport(id: 'viejo')], truncated: false));
    await first;

    expect(state().reports.single.id, 'nuevo');
    expect(state().loading, isFalse);
  });

  test('avisa cuando el área tiene más reportes de los que caben', () async {
    map.truncated = true;

    await controller().showArea(_area);

    expect(state().truncated, isTrue);
  });

  group('confirmar', () {
    test('un reporte ajeno queda confirmado con el total del servidor', () async {
      await controller().showArea(_area);
      await c.read(myReportsProvider.future);
      final pagesBefore = mine.pageOffsets.length;

      await controller().confirm(state().reports.single);

      expect(reports.confirmCalls, ['m1']);
      // Va con la ubicación actual del celular (propuesta 112).
      expect(reports.confirmFixes, [pastoFix]);
      // Desde el mapa no hubo aviso de «Posible duplicado» (objetivo 4).
      expect(reports.confirmWarningIds, [null]);
      final report = state().reports.single;
      expect((report.confirmedByMe, report.confirmations), (true, 4));
      expect((state().confirming, state().confirmedNotice), (false, true));
      // «Mis reportes» se recarga para incluir el confirmado.
      await c.read(myReportsProvider.future);
      expect(mine.pageOffsets.length, pagesBefore + 1);
    });

    test('no se ofrece para el propio, el ya confirmado ni el reparado', () async {
      for (final report in [
        mapReport(isMine: true),
        mapReport(confirmedByMe: true),
        mapReport(status: ReportStatus.repaired),
      ]) {
        expect(report.canConfirm, isFalse);
        await controller().confirm(report);
      }

      expect(reports.confirmCalls, isEmpty);
    });

    test('si ya estaba confirmado se da por hecho, sin aviso', () async {
      await controller().showArea(_area);
      reports.onConfirm = [
        () async => throw const ApiError(
          status: 409,
          code: 'CONFIRMATION_ALREADY_EXISTS',
          message: 'Ya confirmaste este reporte.',
        ),
      ];

      await controller().confirm(state().reports.single);

      expect(state().reports.single.confirmedByMe, isTrue);
      expect((state().confirmError, state().confirmedNotice), (null, false));
    });

    test('un rechazo del servidor muestra su mensaje y deja el reporte igual', () async {
      await controller().showArea(_area);
      reports.onConfirm = [
        () async => throw const ApiError(
          status: 409,
          code: 'REPORT_NOT_ACTIVE',
          message: 'Este reporte ya fue reparado.',
        ),
      ];

      await controller().confirm(state().reports.single);

      expect(state().confirmError, 'Este reporte ya fue reparado.');
      expect(state().reports.single.confirmedByMe, isFalse);
      expect(state().confirming, isFalse);
    });

    test('sin permiso de ubicación lo pide y, si lo niega, explica por qué', () async {
      await controller().showArea(_area);
      location
        ..state = LocationPermissionState.denied
        ..stateAfterRequest = LocationPermissionState.denied;

      await controller().confirm(state().reports.single);

      expect(reports.confirmCalls, isEmpty);
      expect(state().confirmError, confirmLocationDeniedMessage);
      expect(state().confirming, isFalse);
    });

    test('si concede el permiso al pedirlo, confirma', () async {
      await controller().showArea(_area);
      location.state = LocationPermissionState.denied;

      await controller().confirm(state().reports.single);

      expect(reports.confirmCalls, ['m1']);
    });

    test('con el permiso negado para siempre no lo vuelve a pedir', () async {
      await controller().showArea(_area);
      location
        ..state = LocationPermissionState.deniedForever
        ..stateAfterRequest = LocationPermissionState.granted;

      await controller().confirm(state().reports.single);

      expect(reports.confirmCalls, isEmpty);
      expect(state().confirmError, confirmLocationDeniedMessage);
    });

    test('con el GPS apagado pide encenderlo', () async {
      await controller().showArea(_area);
      location.state = LocationPermissionState.serviceDisabled;

      await controller().confirm(state().reports.single);

      expect(reports.confirmCalls, isEmpty);
      expect(state().confirmError, confirmLocationOffMessage);
    });

    test('sin posición del GPS no confirma y lo dice', () async {
      await controller().showArea(_area);
      location.fixes = [];

      await controller().confirm(state().reports.single);

      expect(reports.confirmCalls, isEmpty);
      expect(state().confirmError, confirmLocationUnavailableMessage);
      expect(state().confirming, isFalse);
    });

    test('lejos del daño muestra el mensaje del servidor', () async {
      await controller().showArea(_area);
      reports.onConfirm = [
        () async => throw const ApiError(
          status: 403,
          code: 'CONFIRMATION_TOO_FAR',
          message: 'Para confirmar este daño tienes que estar cerca de él.',
        ),
      ];

      await controller().confirm(state().reports.single);

      expect(state().confirmError, 'Para confirmar este daño tienes que estar cerca de él.');
      expect(state().reports.single.confirmedByMe, isFalse);
    });

    test('sin red muestra el mensaje de conexión', () async {
      await controller().showArea(_area);
      reports.onConfirm = [() async => throw const NetworkFailure()];

      await controller().confirm(state().reports.single);

      expect(state().confirmError, const NetworkFailure().message);
    });
  });

  test('al cerrar la sesión el mapa se vacía', () async {
    await controller().showArea(_area);

    await c.read(sessionControllerProvider.notifier).signOut();

    expect(state().reports, isEmpty);
    expect(state().area, isNull);
  });
}
