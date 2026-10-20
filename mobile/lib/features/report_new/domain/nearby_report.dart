import '../../../core/domain/report_enums.dart';

/// Reporte activo a menos de 25 m (`GET /reports/nearby` y `details.items` del 409). Sin
/// autor ni ubicación exacta: la API solo publica la ubicación redondeada.
class NearbyReport {
  const NearbyReport({
    required this.id,
    required this.distanceMeters,
    required this.status,
    required this.severity,
    required this.confirmations,
    required this.address,
    required this.createdAt,
    required this.isMine,
  });

  final String id;
  final double distanceMeters;
  final ReportStatus status;
  final Severity severity;
  final int confirmations;
  final String address;
  final DateTime createdAt;

  /// Es del propio ciudadano: no puede confirmarlo (propuesta 48).
  final bool isMine;
}

/// Reporte recién creado, tal como lo devolvió el servidor.
class CreatedReport {
  const CreatedReport({required this.id, required this.status, required this.address});

  final String id;
  final ReportStatus status;
  final String address;
}
