import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/session.dart';
import 'package:street_repo/features/report_new/application/report_draft_controller.dart';
import 'package:street_repo/features/report_new/application/submit_report_controller.dart';
import 'package:street_repo/features/report_new/domain/submit_outcome.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/fake_device_services.dart';
import '../../support/fake_new_report_repository.dart';
import '../../support/memory_token_store.dart';

ApiError apiError(int status, String code, {Map<String, dynamic> details = const {}}) =>
    ApiError(status: status, code: code, message: 'Mensaje de $code', details: details);

void main() {
  late FakeNewReportRepository repository;
  late List<Duration> waits;
  late int keys;

  setUp(() {
    repository = FakeNewReportRepository();
    waits = [];
    keys = 0;
  });

  /// Ciudadano en sesión con un borrador completo (foto, ubicación y severidad media).
  Future<ProviderContainer> withDraft() async {
    final store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    final c = ProviderContainer.test(
      overrides: [
        tokenStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(store)),
        locationServiceProvider.overrideWithValue(FakeLocationService()),
        photoServiceProvider.overrideWithValue(FakePhotoService()),
        newReportRepositoryProvider.overrideWithValue(repository),
        idempotencyKeyFactoryProvider.overrideWithValue(() => 'clave-${++keys}'),
        submitRetryWaitProvider.overrideWithValue((delay) async => waits.add(delay)),
      ],
    );
    expect(await c.read(sessionControllerProvider.future), isA<SignedIn>());
    c
      ..listen(reportDraftProvider, (_, _) {})
      ..listen(submitReportProvider, (_, _) {});
    final draft = c.read(reportDraftProvider.notifier);
    await draft.capturePhoto();
    await draft.locate();
    draft.setSeverity(Severity.medium);
    return c;
  }

  SubmitReportController submitter(ProviderContainer c) => c.read(submitReportProvider.notifier);

  group('envío y clave de idempotencia', () {
    test('sin candidatos cercanos crea el reporte y vacía el borrador', () async {
      final c = await withDraft();

      final outcome = await submitter(c).submit();

      expect(outcome, isA<Sent>().having((o) => o.report.id, 'id', 'nuevo'));
      expect(repository.nearbyCalls, hasLength(1));
      expect(repository.createCalls.single.idempotencyKey, 'clave-1');
      expect(repository.createCalls.single.createAnyway, isFalse);
      expect(c.read(reportDraftProvider).photo, isNull);
      expect(c.read(submitReportProvider).outcome, same(outcome));
    });

    test(
      'sin red: conserva el borrador y el reintento usa la misma clave (Review Focus 1)',
      () async {
        final c = await withDraft();
        repository.onCreate = [() async => throw const NetworkFailure(), () async => createdReport];

        final outcome = await submitter(c).submit();

        expect(outcome, isA<Sent>());
        expect(repository.createCalls.map((call) => call.idempotencyKey), ['clave-1', 'clave-1']);
        expect(repository.createCalls.first.draft.photo, isNotNull);
        expect(waits, [submitRetryDelays.first]);
      },
    );

    test('tras agotar los intentos ofrece reintentar sin perder el borrador', () async {
      final c = await withDraft();
      repository.onCreate = [() async => throw const NetworkFailure()];

      final outcome = await submitter(c).submit();

      expect(outcome, isA<SubmitFailed>().having((o) => o.retryable, 'reintentable', isTrue));
      expect(repository.createCalls, hasLength(submitRetryDelays.length + 1));
      expect(waits, submitRetryDelays);
      expect(c.read(reportDraftProvider).hasEvidence, isTrue);
      expect(c.read(reportDraftProvider).idempotencyKey, 'clave-1');
    });

    test(
      '«Reintentar» no vuelve a consultar los cercanos y repite la clave (propuesta 55)',
      () async {
        final c = await withDraft();
        repository.onCreate = [
          () async => throw const NetworkFailure(),
          () async => throw const NetworkFailure(),
          () async => throw const NetworkFailure(),
          () async => createdReport,
        ];
        await submitter(c).submit();

        final outcome = await submitter(c).submit();

        expect(outcome, isA<Sent>());
        expect(repository.nearbyCalls, hasLength(1));
        expect(repository.createCalls.map((call) => call.idempotencyKey).toSet(), {'clave-1'});
      },
    );

    test('cambiar la severidad tras un fallo usa una clave nueva (Review Focus 5)', () async {
      final c = await withDraft();
      repository.onCreate = [
        () async => throw const NetworkFailure(),
        () async => throw const NetworkFailure(),
        () async => throw const NetworkFailure(),
        () async => createdReport,
      ];
      await submitter(c).submit();

      c.read(reportDraftProvider.notifier).setSeverity(Severity.high);
      await submitter(c).submit();

      expect(repository.createCalls.last.idempotencyKey, 'clave-2');
      expect(repository.createCalls.last.draft.severity, Severity.high);
    });

    test('un 5xx también se reintenta solo', () async {
      final c = await withDraft();
      repository.onCreate = [
        () async => throw apiError(503, 'SERVICE_UNAVAILABLE'),
        () async => createdReport,
      ];

      expect(await submitter(c).submit(), isA<Sent>());
      expect(repository.createCalls, hasLength(2));
    });
  });

  group('posible duplicado', () {
    test('los candidatos cercanos detienen el envío', () async {
      final c = await withDraft();
      repository.onNearby = [
        () async => [nearbyReport()],
      ];

      final outcome = await submitter(c).submit();

      expect(
        outcome,
        isA<PossibleDuplicates>().having((o) => o.candidates, 'candidatos', hasLength(1)),
      );
      expect(repository.createCalls, isEmpty);
      expect(c.read(reportDraftProvider).hasEvidence, isTrue);
    });

    test('el 409 por una carrera muestra los candidatos', () async {
      final c = await withDraft();
      repository.onCreate = [
        () async => throw apiError(
          409,
          'REPORT_DUPLICATE_NEARBY',
          details: {
            'radius_m': 25,
            'items': [
              {
                'id': 'r9',
                'location': {'longitude': -77.2811, 'latitude': 1.2136},
                'distance_m': 8.4,
                'status': 'priorizado',
                'severity': 'alta',
                'confirmations': 2,
                'address': 'Carrera 27',
                'created_at': '2026-10-15T15:00:00Z',
                'is_mine': true,
              },
            ],
          },
        ),
      ];

      final outcome = await submitter(c).submit();

      expect(
        outcome,
        isA<PossibleDuplicates>().having((o) => o.candidates.single.isMine, 'propio', isTrue),
      );
    });

    test('«Crear de todos modos» envía create_anyway con la misma clave', () async {
      final c = await withDraft();
      repository.onNearby = [
        () async => [nearbyReport()],
      ];
      await submitter(c).submit();

      final outcome = await submitter(c).createAnyway();

      expect(outcome, isA<Sent>());
      expect(repository.createCalls.single.createAnyway, isTrue);
      expect(repository.createCalls.single.idempotencyKey, 'clave-1');
    });

    test('confirmar devuelve el total y vacía el borrador', () async {
      final c = await withDraft();
      final candidate = nearbyReport();

      final outcome = await submitter(c).confirm(candidate);

      expect(outcome, isA<Confirmed>().having((o) => o.confirmations, 'total', 4));
      expect(repository.confirmCalls, ['r1']);
      expect(c.read(reportDraftProvider).photo, isNull);
    });

    test('si ya lo había confirmado se considera hecho', () async {
      final c = await withDraft();
      repository.onConfirm = [() async => throw apiError(409, 'CONFIRMATION_ALREADY_EXISTS')];

      final outcome = await submitter(c).confirm(nearbyReport(confirmations: 5));

      expect(outcome, isA<Confirmed>().having((o) => o.confirmations, 'total', 5));
    });

    test('un reporte ya reparado no se puede confirmar', () async {
      final c = await withDraft();
      repository.onConfirm = [() async => throw apiError(409, 'REPORT_NOT_ACTIVE')];

      final outcome = await submitter(c).confirm(nearbyReport());

      expect(
        outcome,
        isA<SubmitFailed>()
            .having((o) => o.retryable, 'reintentable', isFalse)
            .having((o) => o.message, 'mensaje', 'Mensaje de REPORT_NOT_ACTIVE'),
      );
      expect(c.read(reportDraftProvider).hasEvidence, isTrue);
    });
  });

  group('errores del envío', () {
    Future<SubmitOutcome> submitFailingWith(ApiFailure failure) async {
      final c = await withDraft();
      repository.onCreate = [() async => throw failure];
      return submitter(c).submit();
    }

    test('fuera del área de servicio', () async {
      expect(
        await submitFailingWith(apiError(422, 'LOCATION_OUTSIDE_SERVICE_AREA')),
        isA<OutsideServiceArea>(),
      );
    });

    test('límite de reportes con Retry-After', () async {
      const failure = ApiError(
        status: 429,
        code: 'REPORT_RATE_LIMITED',
        message: 'Muchos reportes',
        retryAfter: Duration(minutes: 18),
      );
      expect(
        await submitFailingWith(failure),
        isA<RateLimited>().having((o) => o.retryAfter, 'espera', const Duration(minutes: 18)),
      );
    });

    test('el límite de consultas cercanas también es «Límite alcanzado»', () async {
      final c = await withDraft();
      repository.onNearby = [
        () async => throw apiError(429, 'NEARBY_RATE_LIMITED', details: {'retry_after_s': 120}),
      ];

      expect(
        await submitter(c).submit(),
        isA<RateLimited>().having((o) => o.retryAfter, 'espera', const Duration(minutes: 2)),
      );
    });

    for (final (status, code) in [
      (413, 'PHOTO_TOO_LARGE'),
      (415, 'PHOTO_UNSUPPORTED_TYPE'),
      (422, 'PHOTO_INVALID'),
    ]) {
      test('foto rechazada: $code', () async {
        expect(
          await submitFailingWith(apiError(status, code)),
          isA<PhotoRejected>().having((o) => o.message, 'mensaje', 'Mensaje de $code'),
        );
      });
    }

    test('una clave reusada con otros datos se descarta para el siguiente envío', () async {
      final c = await withDraft();
      repository.onCreate = [() async => throw apiError(422, 'IDEMPOTENCY_KEY_REUSED')];

      final outcome = await submitter(c).submit();

      expect(outcome, isA<SubmitFailed>().having((o) => o.retryable, 'reintentable', isTrue));
      expect(c.read(reportDraftProvider).idempotencyKey, isNull);
    });

    test('otro error del servidor se muestra y no se reintenta solo', () async {
      expect(
        await submitFailingWith(apiError(422, 'REPORT_INVALID')),
        isA<SubmitFailed>().having((o) => o.retryable, 'reintentable', isFalse),
      );
      expect(repository.createCalls, hasLength(1));
    });
  });

  test('cerrar sesión olvida el último resultado (propuesta 56)', () async {
    final c = await withDraft();
    await submitter(c).submit();

    await c.read(sessionControllerProvider.notifier).signOut();

    expect(c.read(submitReportProvider).outcome, isNull);
  });
}
