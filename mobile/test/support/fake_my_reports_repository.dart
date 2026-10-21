import 'dart:typed_data';

import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/features/my_reports/domain/my_report.dart';
import 'package:street_repo/features/my_reports/domain/my_reports_repository.dart';
import 'package:street_repo/features/my_reports/domain/report_detail.dart';

import 'fake_device_services.dart';

OwnReport ownReport({
  String id = 'own-1',
  ReportStatus status = ReportStatus.prioritized,
  String? description = 'Bache profundo frente al colegio',
  double? priorityScore = 8.7,
  bool needsRoadReview = false,
  int confirmations = 4,
}) => OwnReport(
  id: id,
  status: status,
  severity: Severity.high,
  address: 'Av. Los Estudiantes',
  confirmations: confirmations,
  createdAt: DateTime.utc(2026, 10, 17, 15),
  description: description,
  priorityScore: priorityScore,
  needsRoadReview: needsRoadReview,
);

ConfirmedReport confirmedReport({
  String id = 'conf-1',
  ReportStatus status = ReportStatus.evaluated,
}) => ConfirmedReport(
  id: id,
  status: status,
  severity: Severity.medium,
  address: 'Calle 18',
  confirmations: 2,
  createdAt: DateTime.utc(2026, 10, 10, 15),
  confirmedAt: DateTime.utc(2026, 10, 19, 15),
);

/// Repositorio falso: devuelve las páginas y detalles que se le indiquen y registra lo pedido.
class FakeMyReportsRepository implements MyReportsRepository {
  /// Todos los reportes; `page` los corta según `offset` y `limit`.
  List<MyReport> reports = [];
  Future<void> Function()? beforePage;
  final List<int> pageOffsets = [];
  final List<String> thumbnailRequests = [];
  Map<String, ReportDetail> details = {};

  @override
  Future<MyReportsPage> page({required int offset, int limit = myReportsPageSize}) async {
    pageOffsets.add(offset);
    await beforePage?.call();
    final end = (offset + limit).clamp(0, reports.length);
    return MyReportsPage(
      items: reports.sublist(offset.clamp(0, reports.length), end),
      total: reports.length,
      limit: limit,
      offset: offset,
    );
  }

  @override
  Future<ReportDetail> detail(String id) async =>
      details[id] ?? (throw StateError('Sin detalle preparado para $id'));

  @override
  Future<Uint8List> thumbnail(String id) async {
    thumbnailRequests.add(id);
    return photoOf(200).jpegBytes;
  }

  @override
  Future<Uint8List> photo(String id) async => photoOf(400).jpegBytes;
}
