import 'dart:typed_data';

import '../../../core/domain/report_enums.dart';

/// Peor precisión del GPS que se acepta: el radio de asociación a la vía (decisión 57). Con
/// más incertidumbre, la vía y los duplicados a 25 m dejarían de ser fiables.
const double maxLocationAccuracyMeters = 30;

/// Lado corto de la foto que se sube. `flutter_image_compress` escala por el lado corto: en
/// una cámara 4:3 deja el largo en 1600 px, el mismo tope con el que el servidor la
/// recodifica (propuesta 35). Nunca agranda una foto más pequeña.
const int photoTargetShortSidePx = 1200;

/// Calidad JPEG en el teléfono, la misma del servidor: la foto viaja liviana por 4G.
const int photoJpegQuality = 85;

/// Largo máximo de la descripción; el mismo que valida la API.
const int descriptionMaxLength = 500;

/// Posición del GPS del teléfono.
class GeoFix {
  const GeoFix({required this.latitude, required this.longitude, required this.accuracyMeters});

  final double latitude;
  final double longitude;

  /// Radio de incertidumbre que informa el GPS, en metros.
  final double accuracyMeters;

  bool get isPreciseEnough => accuracyMeters <= maxLocationAccuracyMeters;

  @override
  bool operator ==(Object other) =>
      other is GeoFix &&
      other.latitude == latitude &&
      other.longitude == longitude &&
      other.accuracyMeters == accuracyMeters;

  @override
  int get hashCode => Object.hash(latitude, longitude, accuracyMeters);
}

/// Foto ya comprimida en JPEG y sin metadatos, lista para subir.
class CapturedPhoto {
  const CapturedPhoto(this.jpegBytes);

  final Uint8List jpegBytes;

  int get sizeBytes => jpegBytes.lengthInBytes;
}

/// Borrador del reporte mientras el ciudadano lo arma. Vive solo en memoria.
///
/// La `idempotencyKey` identifica un envío concreto: cualquier cambio de la foto, la
/// ubicación, la severidad o la descripción la anula, porque reenviar otros datos con la
/// misma clave haría que el servidor respondiera 422 `IDEMPOTENCY_KEY_REUSED`.
class ReportDraft {
  const ReportDraft({
    this.photo,
    this.fix,
    this.severity,
    this.description = '',
    this.idempotencyKey,
  });

  static const empty = ReportDraft();

  final CapturedPhoto? photo;
  final GeoFix? fix;
  final Severity? severity;
  final String description;
  final String? idempotencyKey;

  /// Paso 1 completo: hay foto y una ubicación con la precisión exigida.
  bool get hasEvidence => photo != null && (fix?.isPreciseEnough ?? false);

  /// La ubicación es la del momento de la foto: una foto nueva anula la anterior y hay que
  /// volver a ubicarse.
  ReportDraft withPhoto(CapturedPhoto photo) =>
      ReportDraft(photo: photo, severity: severity, description: description);

  ReportDraft withFix(GeoFix fix) => _changed(fix: fix);

  /// Sin ubicación, para volver a tomarla (p. ej. fuera del área de servicio).
  ReportDraft withoutFix() =>
      ReportDraft(photo: photo, severity: severity, description: description);

  /// Sin foto, porque el servidor la rechazó; la ubicación se toma con la foto nueva.
  ReportDraft withoutPhoto() => ReportDraft(severity: severity, description: description);

  ReportDraft withSeverity(Severity severity) =>
      severity == this.severity ? this : _changed(severity: severity);

  ReportDraft withDescription(String description) =>
      description == this.description ? this : _changed(description: description);

  ReportDraft withIdempotencyKey(String key) => ReportDraft(
    photo: photo,
    fix: fix,
    severity: severity,
    description: description,
    idempotencyKey: key,
  );

  ReportDraft withoutIdempotencyKey() => _changed();

  ReportDraft _changed({
    CapturedPhoto? photo,
    GeoFix? fix,
    Severity? severity,
    String? description,
  }) => ReportDraft(
    photo: photo ?? this.photo,
    fix: fix ?? this.fix,
    severity: severity ?? this.severity,
    description: description ?? this.description,
  );
}
