import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/features/report_map/domain/map_report.dart';
import 'package:street_repo/features/report_map/domain/report_map_repository.dart';

MapReport mapReport({
  String id = 'm1',
  ReportStatus status = ReportStatus.prioritized,
  String address = 'Av. Los Estudiantes',
  int confirmations = 4,
  bool isMine = false,
  bool confirmedByMe = false,
  double latitude = 1.2136,
  double longitude = -77.2811,
}) => MapReport(
  id: id,
  latitude: latitude,
  longitude: longitude,
  status: status,
  severity: Severity.high,
  address: address,
  confirmations: confirmations,
  createdAt: DateTime.utc(2026, 10, 17, 15),
  isMine: isMine,
  confirmedByMe: confirmedByMe,
);

/// Una consulta al mapa, con lo que se pidió.
typedef MapCall = ({MapArea area, ReportStatus? status});

/// Repositorio falso: responde lo que se le indique y registra las consultas. Con filtro
/// devuelve solo los reportes de ese estado, como el servidor.
class FakeReportMapRepository implements ReportMapRepository {
  List<MapReport> reports = [];
  bool truncated = false;
  Future<MapReportsPage> Function(MapArea area, ReportStatus? status)? onList;
  final List<MapCall> calls = [];

  @override
  Future<MapReportsPage> listInArea(MapArea area, {ReportStatus? status}) {
    calls.add((area: area, status: status));
    final custom = onList;
    if (custom != null) return custom(area, status);
    return Future.value(
      MapReportsPage(
        items: [
          for (final report in reports)
            if (status == null || report.status == status) report,
        ],
        truncated: truncated,
      ),
    );
  }
}
