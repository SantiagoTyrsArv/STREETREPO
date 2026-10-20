import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/report_new/data/http_new_report_repository.dart';
import 'package:street_repo/features/report_new/domain/report_draft.dart';

import '../../support/fake_device_services.dart';
import '../../support/fake_http_adapter.dart';

const _candidate = {
  'id': 'r1',
  'location': {'longitude': -77.2811, 'latitude': 1.2136},
  'distance_m': 12.3,
  'status': 'evaluado',
  'severity': 'media',
  'confirmations': 3,
  'address': 'Calle 18',
  'created_at': '2026-10-15T15:00:00Z',
  'is_mine': false,
};

void main() {
  late FakeHttpAdapter adapter;
  late HttpNewReportRepository repository;

  setUp(() {
    adapter = FakeHttpAdapter();
    final dio = Dio(BaseOptions(baseUrl: 'http://api.test/api/v1'))..httpClientAdapter = adapter;
    repository = HttpNewReportRepository(dio);
  });

  final draft = ReportDraft(
    photo: photoOf(100),
    fix: pastoFix,
    severity: Severity.high,
    description: '  Hueco grande  ',
  );

  test('nearby envía el punto y lee los candidatos', () async {
    adapter.reply(
      'GET',
      '/reports/nearby',
      const FakeResponse(
        200,
        body: {
          'radius_m': 25,
          'items': [_candidate],
        },
      ),
    );

    final items = await repository.nearby(pastoFix);

    final query = adapter.requests.single.queryParameters;
    expect(query['latitude'], 1.2136);
    expect(query['longitude'], -77.2811);
    expect(items.single.distanceMeters, 12.3);
    expect(items.single.status, ReportStatus.evaluated);
    expect(items.single.isMine, isFalse);
    expect(items.single.createdAt, DateTime.utc(2026, 10, 15, 15));
  });

  test('create manda la foto, los datos con punto decimal y la clave', () async {
    adapter.reply(
      'POST',
      '/reports',
      const FakeResponse(201, body: {'id': 'nuevo', 'status': 'evaluado', 'address': 'Calle 18'}),
    );

    final created = await repository.create(draft, idempotencyKey: 'k1', createAnyway: true);

    final request = adapter.requests.single;
    expect(request.headers['Idempotency-Key'], 'k1');
    final form = request.data as FormData;
    final fields = Map.fromEntries(form.fields);
    expect(fields['latitude'], '1.2136');
    expect(fields['longitude'], '-77.2811');
    expect(fields['severity'], 'alta');
    expect(fields['description'], 'Hueco grande');
    expect(fields['create_anyway'], 'true');
    expect(form.files.single.key, 'photo');
    expect(form.files.single.value.filename, 'foto.jpg');
    expect(form.files.single.value.contentType.toString(), 'image/jpeg');
    expect(created.id, 'nuevo');
  });

  test('una descripción en blanco no se envía', () async {
    adapter.reply(
      'POST',
      '/reports',
      const FakeResponse(200, body: {'id': 'nuevo', 'status': 'evaluado', 'address': 'Calle 18'}),
    );

    await repository.create(
      draft.withDescription('   '),
      idempotencyKey: 'k1',
      createAnyway: false,
    );

    final fields = Map.fromEntries((adapter.requests.single.data as FormData).fields);
    expect(fields.containsKey('description'), isFalse);
  });

  test('confirm devuelve el total', () async {
    adapter.reply(
      'POST',
      '/reports/r1/confirmations',
      const FakeResponse(201, body: {'report_id': 'r1', 'confirmations': 4}),
    );

    expect(await repository.confirm('r1'), 4);
  });

  test('los errores de la API llegan como ApiError con su código', () async {
    adapter.reply(
      'POST',
      '/reports',
      const FakeResponse(
        422,
        body: {
          'code': 'LOCATION_OUTSIDE_SERVICE_AREA',
          'message': 'Fuera del área',
          'details': {'field': 'location'},
        },
      ),
    );

    await expectLater(
      repository.create(draft, idempotencyKey: 'k1', createAnyway: false),
      throwsA(isA<ApiError>().having((e) => e.code, 'código', 'LOCATION_OUTSIDE_SERVICE_AREA')),
    );
  });

  test('una respuesta con otra forma es UnexpectedFailure', () async {
    adapter.reply('GET', '/reports/nearby', const FakeResponse(200, body: {'items': 'x'}));

    await expectLater(repository.nearby(pastoFix), throwsA(isA<UnexpectedFailure>()));
  });
}
