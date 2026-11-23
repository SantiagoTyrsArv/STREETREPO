import 'nearby_report.dart';
import 'report_draft.dart';

/// Envío del reporte y sus consultas. Los errores llegan como `ApiFailure`.
abstract interface class NewReportRepository {
  /// Reportes activos a 25 m del punto, del más cercano al más lejano, con el id del aviso
  /// que el servidor registró al ofrecerlos.
  Future<NearbyResult> nearby(GeoFix fix);

  /// Crea el reporte con la foto, la ubicación y la severidad del borrador. Un reintento
  /// con la misma [idempotencyKey] no duplica el reporte. Con [createAnyway], el
  /// [duplicateWarningId] del aviso que vio el ciudadano queda como «creó igual».
  Future<CreatedReport> create(
    ReportDraft draft, {
    required String idempotencyKey,
    required bool createAnyway,
    String? duplicateWarningId,
  });

  /// Confirma un reporte ajeno (HU-16) desde [fix], la ubicación actual del ciudadano, y
  /// devuelve el total de confirmaciones. El servidor solo la acepta a 50 m o menos del daño
  /// (propuesta 112). Desde «Posible duplicado», [duplicateWarningId] deja el aviso como
  /// «confirmó»; desde el mapa no hay aviso.
  Future<int> confirm(String reportId, GeoFix fix, {String? duplicateWarningId});
}
