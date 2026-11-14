import '../../../core/domain/report_enums.dart';

/// Rectángulo visible del mapa, en grados WGS 84.
class MapArea {
  const MapArea({required this.west, required this.south, required this.east, required this.north});

  final double west;
  final double south;
  final double east;
  final double north;

  /// Parámetro `bbox` de la API: `min_lon,min_lat,max_lon,max_lat`, con punto decimal.
  String toBbox() => '$west,$south,$east,$north';

  @override
  bool operator ==(Object other) =>
      other is MapArea &&
      other.west == west &&
      other.south == south &&
      other.east == east &&
      other.north == north;

  @override
  int get hashCode => Object.hash(west, south, east, north);
}

/// Reporte en el mapa (`GET /reports`): vista pública, sin autor, descripción ni foto. La
/// ubicación es la aproximada que publica la API, nunca la exacta.
class MapReport {
  const MapReport({
    required this.id,
    required this.latitude,
    required this.longitude,
    required this.status,
    required this.severity,
    required this.address,
    required this.confirmations,
    required this.createdAt,
    required this.isMine,
    required this.confirmedByMe,
  });

  final String id;
  final double latitude;
  final double longitude;
  final ReportStatus status;
  final Severity severity;
  final String address;
  final int confirmations;
  final DateTime createdAt;

  /// Es del propio ciudadano: no puede confirmarlo (propuesta 48).
  final bool isMine;
  final bool confirmedByMe;

  /// El ciudadano puede abrir su detalle (`GET /reports/{id}` solo responde al autor y a
  /// quien lo confirmó).
  bool get canOpenDetail => isMine || confirmedByMe;

  /// Se ofrece «Confirmar este daño»: ajeno, sin confirmar y aún activo. El servidor vuelve
  /// a comprobarlo.
  bool get canConfirm => !isMine && !confirmedByMe && status != ReportStatus.repaired;

  MapReport confirmed(int total) => MapReport(
    id: id,
    latitude: latitude,
    longitude: longitude,
    status: status,
    severity: severity,
    address: address,
    confirmations: total,
    createdAt: createdAt,
    isMine: isMine,
    confirmedByMe: true,
  );
}

/// Reportes del área visible. [truncated] indica que el área tiene más de los que caben en
/// una respuesta: hay que acercar el mapa.
class MapReportsPage {
  const MapReportsPage({required this.items, required this.truncated});

  final List<MapReport> items;
  final bool truncated;
}
