import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/features/my_reports/data/http_my_reports_repository.dart';
import 'package:street_repo/features/my_reports/domain/my_report.dart';
import 'package:street_repo/features/my_reports/domain/report_detail.dart';

import '../../support/fake_http_adapter.dart';

// Copiados de las respuestas de la API (OwnReportItem, ConfirmedReportItem y el detalle).
const _own = {
  'relation': 'own',
  'id': 'r1',
  'status': 'priorizado',
  'severity': 'alta',
  'description': 'Bache profundo',
  'location': {'longitude': -77.2811, 'latitude': 1.2136},
  'address': 'Av. Los Estudiantes',
  'priority_score': '8.70',
  'needs_road_review': false,
  'created_at': '2026-10-12T15:00:00Z',
  'confirmations': 4,
};

const _confirmed = {
  'relation': 'confirmed',
  'id': 'r2',
  'location': {'longitude': -77.2811, 'latitude': 1.2136},
  'status': 'evaluado',
  'severity': 'media',
  'address': 'Calle 18',
  'confirmations': 2,
  'created_at': '2026-10-10T15:00:00Z',
  'confirmed_at': '2026-10-19T15:00:00Z',
};

/// Una respuesta de ejemplo con campos cambiados o añadidos.
Map<String, Object?> _with(Map<String, Object?> base, Map<String, Object?> changes) => {
  ...base,
  ...changes,
};

void main() {
  late FakeHttpAdapter adapter;
  late HttpMyReportsRepository repository;

  setUp(() {
    adapter = FakeHttpAdapter();
    final dio = Dio(BaseOptions(baseUrl: 'http://api.test/api/v1'))..httpClientAdapter = adapter;
    repository = HttpMyReportsRepository(dio);
  });

  test('lee los reportes propios y los confirmados de una página', () async {
    adapter.reply(
      'GET',
      '/me/reports',
      const FakeResponse(
        200,
        body: {
          'items': [_own, _confirmed],
          'total': 2,
          'limit': 20,
          'offset': 0,
        },
      ),
    );

    final page = await repository.page(offset: 0);

    expect(adapter.requests.single.queryParameters, {'limit': 20, 'offset': 0});
    final own = page.items.first as OwnReport;
    expect(own.priorityScore, 8.7);
    expect(own.description, 'Bache profundo');
    expect(own.status, ReportStatus.prioritized);
    final confirmed = page.items.last as ConfirmedReport;
    expect(confirmed.confirmedAt, DateTime.utc(2026, 10, 19, 15));
    expect(confirmed.relatedAt, confirmed.confirmedAt);
    expect(page.hasMore, isFalse);
  });

  test('hasMore es verdadero si faltan reportes por pedir', () {
    const page = MyReportsPage(items: [], total: 25, limit: 20, offset: 0);
    expect(page.hasMore, isTrue);
  });

  test('el detalle de un administrador trae la vista completa', () async {
    adapter.reply(
      'GET',
      '/reports/r1',
      FakeResponse(
        200,
        body: _with(_own, {
          'relation': 'staff',
          'history': [
            {'status': 'registrado', 'changed_at': '2026-10-12T15:00:00Z', 'note': null},
            {'status': 'priorizado', 'changed_at': '2026-10-14T15:00:00Z', 'note': 'Cuadrilla'},
          ],
        }),
      ),
    );

    final detail = await repository.detail('r1');

    expect(detail.relation, ReportRelation.staff);
    expect(detail.isFullView, isTrue);
    expect(detail.isMine, isFalse);
    expect(detail.report, isA<OwnReport>());
    expect(detail.history.last.note, 'Cuadrilla');
  });

  test('el detalle de quien confirmó es la vista limitada', () async {
    adapter.reply(
      'GET',
      '/reports/r2',
      FakeResponse(
        200,
        body: _with(_confirmed, {
          'history': [
            {'status': 'registrado', 'changed_at': '2026-10-10T15:00:00Z', 'note': null},
          ],
        }),
      ),
    );

    final detail = await repository.detail('r2');

    expect(detail.relation, ReportRelation.confirmed);
    expect(detail.isFullView, isFalse);
    expect(detail.report, isA<ConfirmedReport>());
  });

  test('la miniatura llega como bytes por el mismo cliente', () async {
    adapter.on(
      'GET',
      '/reports/r1/photo/thumbnail',
      (_) async => const FakeResponse(200, body: 'jpeg'),
    );

    final bytes = await repository.thumbnail('r1');

    expect(bytes, isNotEmpty);
    expect(adapter.requests.single.responseType, ResponseType.bytes);
  });
}
