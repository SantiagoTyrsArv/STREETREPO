import 'nearby_report.dart';
import 'report_draft.dart';

/// Envío del reporte y sus consultas. Los errores llegan como `ApiFailure`.
abstract interface class NewReportRepository {
  /// Reportes activos a 25 m del punto, del más cercano al más lejano.
  Future<List<NearbyReport>> nearby(GeoFix fix);

  /// Crea el reporte con la foto, la ubicación y la severidad del borrador. Un reintento
  /// con la misma [idempotencyKey] no duplica el reporte.
  Future<CreatedReport> create(
    ReportDraft draft, {
    required String idempotencyKey,
    required bool createAnyway,
  });

  /// Confirma un reporte ajeno (HU-16) y devuelve el total de confirmaciones.
  Future<int> confirm(String reportId);
}
