import '../../../core/domain/report_enums.dart';

/// Un reporte de «Mis reportes»: creado por el ciudadano o confirmado por él (decisión 49).
sealed class MyReport {
  const MyReport({
    required this.id,
    required this.status,
    required this.severity,
    required this.address,
    required this.confirmations,
    required this.createdAt,
  });

  final String id;
  final ReportStatus status;
  final Severity severity;

  /// Nombre de la vía o el texto de reserva del servidor (decisión 60).
  final String address;
  final int confirmations;
  final DateTime createdAt;

  /// Fecha de la relación del ciudadano con el reporte: la de creación o la de confirmación.
  DateTime get relatedAt;
}

/// Reporte creado por el ciudadano: vista completa.
final class OwnReport extends MyReport {
  const OwnReport({
    required super.id,
    required super.status,
    required super.severity,
    required super.address,
    required super.confirmations,
    required super.createdAt,
    required this.description,
    required this.priorityScore,
    required this.needsRoadReview,
  });

  final String? description;

  /// Urgencia U en escala 0-10; null si aún no se evaluó.
  final double? priorityScore;

  /// No hay vía OSM a 30 m: el administrador debe revisar la vía.
  final bool needsRoadReview;

  @override
  DateTime get relatedAt => createdAt;
}

/// Reporte ajeno que el ciudadano confirmó: vista pública, sin descripción ni foto.
final class ConfirmedReport extends MyReport {
  const ConfirmedReport({
    required super.id,
    required super.status,
    required super.severity,
    required super.address,
    required super.confirmations,
    required super.createdAt,
    required this.confirmedAt,
  });

  final DateTime confirmedAt;

  @override
  DateTime get relatedAt => confirmedAt;
}

class MyReportsPage {
  const MyReportsPage({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
  });

  final List<MyReport> items;
  final int total;
  final int limit;
  final int offset;

  bool get hasMore => offset + items.length < total;
}
