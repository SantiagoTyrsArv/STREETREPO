import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/report_map/data/http_report_map_repository.dart';
import 'package:street_repo/features/report_map/domain/map_report.dart';

import '../../support/fake_http_adapter.dart';

const _area = MapArea(west: -77.29, south: 1.2, east: -77.27, north: 1.22);

const _item = {
  'id': 'r1',
  'location': {'longitude': -77.2811, 'latitude': 1.2137},
  'status': 'priorizado',
  'severity': 'alta',
  'address': 'Avenida Los Estudiantes',
  'confirmations': 4,
  'created_at': '2026-10-19T12:00:00Z',
  'is_mine': false,
  'confirmed_by_me': true,
};

void main() {
  late FakeHttpAdapter adapter;
  late HttpReportMapRepository repository;

  setUp(() {
    adapter = FakeHttpAdapter();
    final dio = Dio(BaseOptions(baseUrl: 'http://api.test/api/v1'))..httpClientAdapter = adapter;
    repository = HttpReportMapRepository(dio);
  });

  test('pide el área visible y lee la vista pública de cada reporte', () async {
    adapter.reply(
      'GET',
      '/reports',
      const FakeResponse(
        200,
        body: {
          'items': [_item],
          'limit': 200,
          'truncated': true,
        },
      ),
    );

    final page = await repository.listInArea(_area);

    expect(adapter.requests.single.queryParameters, {'bbox': '-77.29,1.2,-77.27,1.22'});
    expect(page.truncated, isTrue);
    final report = page.items.single;
    expect(report.id, 'r1');
    expect((report.latitude, report.longitude), (1.2137, -77.2811));
    expect(report.status, ReportStatus.prioritized);
    expect(report.severity, Severity.high);
    expect(report.address, 'Avenida Los Estudiantes');
    expect(report.confirmations, 4);
    expect(report.createdAt, DateTime.utc(2026, 10, 19, 12));
    expect((report.isMine, report.confirmedByMe), (false, true));
  });

  test('envía el filtro de estado con el valor de la API', () async {
    adapter.reply(
      'GET',
      '/reports',
      const FakeResponse(200, body: {'items': <Object>[], 'limit': 200, 'truncated': false}),
    );

    final page = await repository.listInArea(_area, status: ReportStatus.repaired);

    expect(adapter.requests.single.queryParameters['status'], 'reparado');
    expect(page.items, isEmpty);
  });

  test('coordenadas enteras en el JSON también se leen', () async {
    final item = Map<String, Object?>.of(_item)..['location'] = {'longitude': -80, 'latitude': 0};
    adapter.reply(
      'GET',
      '/reports',
      FakeResponse(
        200,
        body: {
          'items': [item],
          'limit': 200,
          'truncated': false,
        },
      ),
    );

    final report = (await repository.listInArea(_area)).items.single;

    expect((report.latitude, report.longitude), (0.0, -80.0));
  });

  test('el límite de consultas llega como ApiError con su espera', () async {
    adapter.reply(
      'GET',
      '/reports',
      FakeResponse(
        429,
        body: errorBody('REPORTS_LIST_RATE_LIMITED'),
        headers: const {
          'retry-after': ['20'],
        },
      ),
    );

    await expectLater(
      repository.listInArea(_area),
      throwsA(
        isA<ApiError>()
            .having((e) => e.code, 'code', 'REPORTS_LIST_RATE_LIMITED')
            .having((e) => e.retryAfter, 'espera', const Duration(seconds: 20)),
      ),
    );
  });

  test('sin red es NetworkFailure', () async {
    adapter.on(
      'GET',
      '/reports',
      (options) =>
          throw DioException(requestOptions: options, type: DioExceptionType.connectionError),
    );

    await expectLater(repository.listInArea(_area), throwsA(isA<NetworkFailure>()));
  });

  test('una respuesta con otra forma es UnexpectedFailure', () async {
    adapter.reply(
      'GET',
      '/reports',
      const FakeResponse(
        200,
        body: {
          'items': [
            {'id': 'r1'},
          ],
          'truncated': false,
        },
      ),
    );

    await expectLater(repository.listInArea(_area), throwsA(isA<UnexpectedFailure>()));
  });
}
