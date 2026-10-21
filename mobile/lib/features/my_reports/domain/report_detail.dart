import '../../../core/domain/report_enums.dart';
import 'my_report.dart';

/// Relación de quien mira el detalle con el reporte.
enum ReportRelation {
  /// Su autor: vista completa.
  own,

  /// Un administrador que no es el autor: la misma vista completa.
  staff,

  /// Lo confirmó: vista limitada, sin foto, urgencia ni observaciones.
  confirmed,
}

/// Un cambio de estado del historial, del más antiguo al más reciente.
class HistoryEntry {
  const HistoryEntry({required this.status, required this.changedAt, this.note});

  final ReportStatus status;
  final DateTime changedAt;

  /// Observación del cambio; null para quien solo confirmó el reporte.
  final String? note;
}

/// Detalle de `GET /reports/{id}`.
class ReportDetail {
  const ReportDetail({required this.relation, required this.report, required this.history});

  final ReportRelation relation;
  final MyReport report;
  final List<HistoryEntry> history;

  bool get isMine => relation == ReportRelation.own;

  /// Vista completa: foto, urgencia y «Revisar vía».
  bool get isFullView => relation != ReportRelation.confirmed;
}
