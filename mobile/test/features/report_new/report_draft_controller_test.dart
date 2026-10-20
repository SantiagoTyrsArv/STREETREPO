import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/session.dart';
import 'package:street_repo/features/report_new/application/report_draft_controller.dart';
import 'package:street_repo/features/report_new/domain/device_services.dart';
import 'package:street_repo/features/report_new/domain/report_draft.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/fake_device_services.dart';
import '../../support/memory_token_store.dart';

void main() {
  late FakeLocationService location;
  late FakePhotoService photos;
  late MemoryTokenStore store;
  late FakeAuthRepository auth;

  setUp(() {
    location = FakeLocationService();
    photos = FakePhotoService();
    store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    auth = FakeAuthRepository(store);
  });

  /// Contenedor con el ciudadano de prueba ya en sesión.
  Future<ProviderContainer> signedIn() async {
    final c = ProviderContainer.test(
      overrides: [
        tokenStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(auth),
        locationServiceProvider.overrideWithValue(location),
        photoServiceProvider.overrideWithValue(photos),
      ],
    );
    expect(await c.read(sessionControllerProvider.future), isA<SignedIn>());
    c.listen(reportDraftProvider, (_, _) {});
    return c;
  }

  group('ubicación (decisión 57)', () {
    test('la precisión mínima es el radio de asociación a la vía, 30 m', () {
      expect(maxLocationAccuracyMeters, 30);
    });

    test('una ubicación de ±72 m no completa el paso 1', () async {
      final c = await signedIn();
      location.fixes = [fixWithAccuracy(72)];

      final outcome = await c.read(reportDraftProvider.notifier).locate();

      expect(outcome, isA<LocationTooImprecise>().having((o) => o.accuracyMeters, 'precisión', 72));
      expect(c.read(reportDraftProvider).fix, isNull);
    });

    test('exactamente 30 m se acepta', () async {
      final c = await signedIn();
      location.fixes = [fixWithAccuracy(30)];

      final outcome = await c.read(reportDraftProvider.notifier).locate();

      expect(outcome, isA<Located>());
      expect(c.read(reportDraftProvider).fix?.accuracyMeters, 30);
    });

    test('con el GPS apagado informa el problema de acceso sin pedir posición', () async {
      final c = await signedIn();
      location.state = LocationPermissionState.serviceDisabled;

      final outcome = await c.read(reportDraftProvider.notifier).locate();

      expect(
        outcome,
        isA<LocationAccessProblem>().having(
          (o) => o.state,
          'estado',
          LocationPermissionState.serviceDisabled,
        ),
      );
      expect(location.fixRequests, 0);
    });

    test('sin ninguna posición a tiempo responde LocationNotFound', () async {
      final c = await signedIn();
      location.fixes = [];

      expect(await c.read(reportDraftProvider.notifier).locate(), isA<LocationNotFound>());
    });
  });

  group('foto', () {
    test('cancelar la cámara conserva la foto anterior', () async {
      final c = await signedIn();
      final controller = c.read(reportDraftProvider.notifier);
      final first = photoOf(10);
      photos.nextPhoto = first;
      await controller.capturePhoto();

      photos.nextPhoto = null;
      final taken = await controller.capturePhoto();

      expect(taken, isFalse);
      expect(c.read(reportDraftProvider).photo, same(first));
    });

    test('una foto nueva exige volver a ubicarse', () async {
      final c = await signedIn();
      final controller = c.read(reportDraftProvider.notifier);
      await controller.capturePhoto();
      await controller.locate();
      expect(c.read(reportDraftProvider).hasEvidence, isTrue);

      photos.nextPhoto = photoOf(20);
      await controller.capturePhoto();

      expect(c.read(reportDraftProvider).fix, isNull);
      expect(c.read(reportDraftProvider).hasEvidence, isFalse);
    });
  });

  group('clave de idempotencia (Review Focus 5)', () {
    const keyed = ReportDraft(
      fix: pastoFix,
      severity: Severity.medium,
      description: 'Hueco',
      idempotencyKey: 'k1',
    );

    test('cambiar la severidad, la descripción o la ubicación anula la clave', () {
      expect(keyed.withSeverity(Severity.high).idempotencyKey, isNull);
      expect(keyed.withDescription('Hueco grande').idempotencyKey, isNull);
      expect(keyed.withFix(fixWithAccuracy(8)).idempotencyKey, isNull);
      expect(keyed.withPhoto(photoOf(5)).idempotencyKey, isNull);
    });

    test('repetir el mismo valor conserva la clave', () {
      expect(keyed.withSeverity(Severity.medium).idempotencyKey, 'k1');
      expect(keyed.withDescription('Hueco').idempotencyKey, 'k1');
    });
  });

  group('datos del ciudadano al cerrar la sesión (propuesta 56)', () {
    Future<ProviderContainer> withDraft() async {
      final c = await signedIn();
      final controller = c.read(reportDraftProvider.notifier);
      await controller.capturePhoto();
      await controller.locate();
      controller.setSeverity(Severity.high);
      expect(c.read(reportDraftProvider).hasEvidence, isTrue);
      return c;
    }

    test('cerrar sesión vacía el borrador y borra la foto temporal', () async {
      final c = await withDraft();

      await c.read(sessionControllerProvider.notifier).signOut();

      final draft = c.read(reportDraftProvider);
      expect(draft.photo, isNull);
      expect(draft.fix, isNull);
      expect(draft.severity, isNull);
      expect(photos.discards, 1);
    });

    test('al vencer la sesión también se vacía', () async {
      final c = await withDraft();

      c.read(sessionControllerProvider.notifier).expire();

      expect(c.read(reportDraftProvider).photo, isNull);
      expect(photos.discards, 1);
    });

    test('si entra otra persona no ve el borrador anterior', () async {
      final c = await withDraft();
      auth.onMe = () async =>
          const UserProfile(id: 'u2', name: 'Luis', email: 'luis@correo.co', role: 'ciudadano');

      await c
          .read(sessionControllerProvider.notifier)
          .signIn(email: 'luis@correo.co', password: 'otra-clave');

      expect(c.read(reportDraftProvider).photo, isNull);
      expect(photos.discards, 1);
    });

    test('los cambios del borrador no borran la foto temporal', () async {
      await withDraft();

      expect(photos.discards, 0);
    });
  });
}
