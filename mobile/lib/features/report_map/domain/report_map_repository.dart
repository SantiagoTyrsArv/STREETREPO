import '../../../core/domain/report_enums.dart';
import 'map_report.dart';

/// Reportes para el mapa. Los fallos llegan como `ApiFailure`.
abstract interface class ReportMapRepository {
  /// Reportes de [area], del más reciente al más antiguo; [status] filtra por estado.
  Future<MapReportsPage> listInArea(MapArea area, {ReportStatus? status});
}
