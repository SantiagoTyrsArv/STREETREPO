import 'dart:typed_data';

import 'package:street_repo/features/report_new/domain/device_services.dart';
import 'package:street_repo/features/report_new/domain/report_draft.dart';

const pastoFix = GeoFix(latitude: 1.2136, longitude: -77.2811, accuracyMeters: 12);

GeoFix fixWithAccuracy(double meters) =>
    GeoFix(latitude: 1.2136, longitude: -77.2811, accuracyMeters: meters);

/// PNG de 1×1 válido (para que `Image.memory` lo pinte), rellenado hasta [size] bytes.
CapturedPhoto photoOf(int size) {
  final bytes = Uint8List(size < _png1x1.length ? _png1x1.length : size)
    ..setRange(0, _png1x1.length, _png1x1);
  return CapturedPhoto(bytes);
}

const _png1x1 = [
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, //
  0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, //
  0x15, 0xC4, 0x89, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0xF8, //
  0xCF, 0xC0, 0xF0, 0x1F, 0x00, 0x05, 0x00, 0x01, 0xFF, 0x89, 0x99, 0x3D, 0x1D, 0x00, 0x00, //
  0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82, //
];

/// GPS falso: el permiso y las posiciones que se le indiquen; registra los ajustes abiertos.
class FakeLocationService implements LocationService {
  LocationPermissionState state = LocationPermissionState.granted;
  LocationPermissionState stateAfterRequest = LocationPermissionState.granted;

  /// Posiciones que irá devolviendo `currentFix`; la última se repite. Vacía → sin posición.
  List<GeoFix> fixes = [pastoFix];
  int fixRequests = 0;
  final List<LocationPermissionState> openedSettings = [];

  @override
  Future<LocationPermissionState> permission() async => state;

  @override
  Future<LocationPermissionState> request() async => state = stateAfterRequest;

  @override
  Future<GeoFix> currentFix() async {
    fixRequests++;
    if (fixes.isEmpty) throw const LocationUnavailable();
    return fixes.length == 1 ? fixes.first : fixes.removeAt(0);
  }

  @override
  Future<void> openSettings(LocationPermissionState state) async => openedSettings.add(state);
}

/// Cámara falsa: devuelve [nextPhoto] (null = el ciudadano canceló) o lanza si [fails].
class FakePhotoService implements PhotoService {
  CapturedPhoto? nextPhoto = photoOf(600 * 1024);
  bool fails = false;
  int discards = 0;

  @override
  Future<CapturedPhoto?> takePhoto() async {
    if (fails) throw const PhotoCaptureFailed();
    return nextPhoto;
  }

  @override
  Future<void> discardTemporaryFiles() async => discards++;
}
