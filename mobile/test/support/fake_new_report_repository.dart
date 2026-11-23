import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/features/report_new/domain/nearby_report.dart';
import 'package:street_repo/features/report_new/domain/new_report_repository.dart';
import 'package:street_repo/features/report_new/domain/report_draft.dart';

NearbyReport nearbyReport({
  String id = 'r1',
  double distance = 12,
  int confirmations = 3,
  bool isMine = false,
}) => NearbyReport(
  id: id,
  distanceMeters: distance,
  status: ReportStatus.evaluated,
  severity: Severity.medium,
  confirmations: confirmations,
  address: 'Calle 18',
  createdAt: DateTime.utc(2026, 10, 15, 15),
  isMine: isMine,
);

const createdReport = CreatedReport(
  id: 'nuevo',
  status: ReportStatus.evaluated,
  address: 'Calle 18',
);

/// Una llamada a `create`, con lo que se envió.
class CreateCall {
  const CreateCall(
    this.draft,
    this.idempotencyKey, {
    required this.createAnyway,
    this.duplicateWarningId,
  });

  final ReportDraft draft;
  final String idempotencyKey;
  final bool createAnyway;
  final String? duplicateWarningId;
}

/// Repositorio falso: cada operación responde lo que se le indique y registra las llamadas.
/// Las respuestas en cola se consumen en orden; la última se repite.
class FakeNewReportRepository implements NewReportRepository {
  List<Future<NearbyResult> Function()> onNearby = [() async => const NearbyResult(candidates: [])];
  List<Future<CreatedReport> Function()> onCreate = [() async => createdReport];
  List<Future<int> Function()> onConfirm = [() async => 4];

  final List<GeoFix> nearbyCalls = [];
  final List<CreateCall> createCalls = [];
  final List<String> confirmCalls = [];

  /// Aviso de duplicado enviado con cada confirmación (`null` desde el mapa).
  final List<String?> confirmWarningIds = [];

  /// Ubicación enviada con cada confirmación (propuesta 112).
  final List<GeoFix> confirmFixes = [];

  static T _next<T>(List<T> queue) => queue.length == 1 ? queue.first : queue.removeAt(0);

  @override
  Future<NearbyResult> nearby(GeoFix fix) {
    nearbyCalls.add(fix);
    return _next(onNearby)();
  }

  @override
  Future<CreatedReport> create(
    ReportDraft draft, {
    required String idempotencyKey,
    required bool createAnyway,
    String? duplicateWarningId,
  }) {
    createCalls.add(
      CreateCall(
        draft,
        idempotencyKey,
        createAnyway: createAnyway,
        duplicateWarningId: duplicateWarningId,
      ),
    );
    return _next(onCreate)();
  }

  @override
  Future<int> confirm(String reportId, GeoFix fix, {String? duplicateWarningId}) {
    confirmCalls.add(reportId);
    confirmWarningIds.add(duplicateWarningId);
    confirmFixes.add(fix);
    return _next(onConfirm)();
  }
}
