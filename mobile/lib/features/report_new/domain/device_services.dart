import 'report_draft.dart';

enum LocationPermissionState {
  granted,

  /// Aún no se ha pedido, o se negó una vez: se puede volver a pedir.
  denied,

  /// Negado de forma permanente: solo se cambia en los ajustes del teléfono.
  deniedForever,

  /// Permiso concedido, pero el GPS del teléfono está apagado.
  serviceDisabled,
}

/// GPS del teléfono, detrás de una interfaz propia para probar sin dispositivo.
abstract interface class LocationService {
  Future<LocationPermissionState> permission();

  Future<LocationPermissionState> request();

  /// La mejor posición que se obtenga en un tiempo límite; puede ser menos precisa que
  /// [maxLocationAccuracyMeters]. Lanza [LocationUnavailable] si no hay ninguna.
  Future<GeoFix> currentFix();

  /// Ajustes de ubicación si el GPS está apagado; si no, los de la app.
  Future<void> openSettings(LocationPermissionState state);
}

class LocationUnavailable implements Exception {
  const LocationUnavailable();
}

/// Cámara trasera del teléfono. Devuelve la foto comprimida y sin metadatos, o null si el
/// ciudadano cancela. Lanza [PhotoCaptureFailed] si la cámara o la compresión fallan.
abstract interface class PhotoService {
  Future<CapturedPhoto?> takePhoto();

  /// Borra del disco las fotos temporales de la cámara que aún queden (propuesta 56). Se
  /// llama al cerrar o vencer la sesión; nunca lanza.
  Future<void> discardTemporaryFiles();
}

class PhotoCaptureFailed implements Exception {
  const PhotoCaptureFailed();
}
