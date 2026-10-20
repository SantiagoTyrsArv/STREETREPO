import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/domain/report_enums.dart';
import '../../auth/application/session_controller.dart';
import '../data/geolocator_location_service.dart';
import '../data/picker_photo_service.dart';
import '../domain/device_services.dart';
import '../domain/report_draft.dart';

final locationServiceProvider = Provider<LocationService>(
  (ref) => const GeolocatorLocationService(),
);

final photoServiceProvider = Provider<PhotoService>((ref) => PickerPhotoService());

/// Resultado de pedir la ubicación para el borrador.
sealed class LocateOutcome {
  const LocateOutcome();
}

final class Located extends LocateOutcome {
  const Located(this.fix);

  final GeoFix fix;
}

/// El GPS respondió, pero con más incertidumbre que [maxLocationAccuracyMeters].
final class LocationTooImprecise extends LocateOutcome {
  const LocationTooImprecise(this.accuracyMeters);

  final double accuracyMeters;
}

/// Falta el permiso o el GPS está apagado.
final class LocationAccessProblem extends LocateOutcome {
  const LocationAccessProblem(this.state);

  final LocationPermissionState state;
}

/// No llegó ninguna posición a tiempo.
final class LocationNotFound extends LocateOutcome {
  const LocationNotFound();
}

/// Borrador del reporte en curso. Depende del ciudadano en sesión: al cerrar o vencer la
/// sesión, o al entrar otra persona, vuelve a vacío, la foto sale de la memoria y se borran
/// del disco las fotos temporales de la cámara (propuesta 56).
final reportDraftProvider = NotifierProvider<ReportDraftController, ReportDraft>(
  ReportDraftController.new,
);

class ReportDraftController extends Notifier<ReportDraft> {
  @override
  ReportDraft build() {
    ref.watch(currentUserIdProvider);
    // Solo un cambio de ciudadano reconstruye el borrador, y antes se descarta el anterior.
    final photos = ref.read(photoServiceProvider);
    ref.onDispose(() => unawaited(photos.discardTemporaryFiles()));
    return ReportDraft.empty;
  }

  LocationService get _location => ref.read(locationServiceProvider);

  Future<LocationPermissionState> locationAccess() => _location.permission();

  Future<LocationPermissionState> requestLocationAccess() => _location.request();

  Future<void> openLocationSettings(LocationPermissionState state) => _location.openSettings(state);

  /// Toma la foto. Devuelve false si el ciudadano canceló: la foto anterior se conserva.
  Future<bool> capturePhoto() async {
    final photo = await ref.read(photoServiceProvider).takePhoto();
    if (photo == null || !ref.mounted) return false;
    state = state.withPhoto(photo);
    return true;
  }

  /// Pide la ubicación actual. Solo la guarda en el borrador si es lo bastante precisa: el
  /// paso 1 no se completa con una ubicación peor que [maxLocationAccuracyMeters].
  Future<LocateOutcome> locate() async {
    final access = await _location.permission();
    if (access != LocationPermissionState.granted) return LocationAccessProblem(access);
    final GeoFix fix;
    try {
      fix = await _location.currentFix();
    } on LocationUnavailable {
      return const LocationNotFound();
    }
    if (!fix.isPreciseEnough) return LocationTooImprecise(fix.accuracyMeters);
    if (ref.mounted) state = state.withFix(fix);
    return Located(fix);
  }

  void setSeverity(Severity severity) => state = state.withSeverity(severity);

  void setDescription(String description) => state = state.withDescription(description);

  /// Guarda la clave del envío antes de mandarlo, para que los reintentos la reutilicen.
  void setIdempotencyKey(String key) => state = state.withIdempotencyKey(key);

  /// Olvida la clave del envío: el siguiente se trata como un reporte nuevo.
  void clearIdempotencyKey() => state = state.withoutIdempotencyKey();

  void discardLocation() => state = state.withoutFix();

  void discardPhoto() => state = state.withoutPhoto();

  void reset() => state = ReportDraft.empty;
}
