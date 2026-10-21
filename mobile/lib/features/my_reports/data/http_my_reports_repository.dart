import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../../core/domain/report_enums.dart';
import '../../../core/network/api_error.dart';
import '../domain/my_report.dart';
import '../domain/my_reports_repository.dart';
import '../domain/report_detail.dart';

/// `GET /me/reports`, `GET /reports/{id}` y las fotos. Traduce los errores a `ApiFailure`;
/// una respuesta con otra forma es `UnexpectedFailure`.
class HttpMyReportsRepository implements MyReportsRepository {
  HttpMyReportsRepository(this._dio);

  final Dio _dio;

  @override
  Future<MyReportsPage> page({required int offset, int limit = myReportsPageSize}) => _call(
    () async {
      final json = _json(
        await _dio.get<Object?>('/me/reports', queryParameters: {'limit': limit, 'offset': offset}),
      );
      final items = json['items'];
      if (items is! List<Object?>) throw const FormatException('Faltan los reportes');
      return MyReportsPage(
        items: [for (final item in items) parseMyReport(_map(item))],
        total: _field<int>(json, 'total'),
        limit: _field<int>(json, 'limit'),
        offset: _field<int>(json, 'offset'),
      );
    },
  );

  @override
  Future<ReportDetail> detail(String id) => _call(() async {
    final json = _json(await _dio.get<Object?>('/reports/$id'));
    final history = json['history'];
    if (history is! List<Object?>) throw const FormatException('Falta el historial');
    return ReportDetail(
      relation: switch (_field<String>(json, 'relation')) {
        'own' => ReportRelation.own,
        'staff' => ReportRelation.staff,
        'confirmed' => ReportRelation.confirmed,
        final other => throw FormatException('Relación desconocida: $other'),
      },
      report: parseMyReport(json),
      history: [
        for (final entry in history.map(_map))
          HistoryEntry(
            status: ReportStatus.fromApi(_field<String>(entry, 'status')),
            changedAt: DateTime.parse(_field<String>(entry, 'changed_at')),
            note: switch (entry['note']) {
              final String value => value,
              _ => null,
            },
          ),
      ],
    );
  });

  @override
  Future<Uint8List> thumbnail(String id) => _bytes('/reports/$id/photo/thumbnail');

  @override
  Future<Uint8List> photo(String id) => _bytes('/reports/$id/photo');

  Future<Uint8List> _bytes(String path) => _call(() async {
    final response = await _dio.get<List<int>>(
      path,
      options: Options(responseType: ResponseType.bytes),
    );
    final data = response.data;
    if (data == null || data.isEmpty) throw const FormatException('La foto llegó vacía');
    return Uint8List.fromList(data);
  });

  static Future<T> _call<T>(Future<T> Function() request) async {
    try {
      return await request();
    } on DioException catch (e) {
      throw ApiFailure.fromDioException(e);
    } on FormatException {
      throw const UnexpectedFailure();
    }
  }

  static Map<String, dynamic> _json(Response<Object?> response) => _map(response.data);
}

/// Un elemento de `GET /me/reports` (o la parte común del detalle), según `relation`.
/// El detalle de un administrador (`staff`) trae la misma vista que el del autor.
MyReport parseMyReport(Map<String, dynamic> json) {
  final id = _field<String>(json, 'id');
  final status = ReportStatus.fromApi(_field<String>(json, 'status'));
  final severity = Severity.fromApi(_field<String>(json, 'severity'));
  final address = _field<String>(json, 'address');
  final confirmations = _field<int>(json, 'confirmations');
  final createdAt = DateTime.parse(_field<String>(json, 'created_at'));
  return switch (_field<String>(json, 'relation')) {
    'own' || 'staff' => OwnReport(
      id: id,
      status: status,
      severity: severity,
      address: address,
      confirmations: confirmations,
      createdAt: createdAt,
      description: switch (json['description']) {
        final String value => value,
        _ => null,
      },
      // La API manda el decimal como texto («8.70») para no perder precisión.
      priorityScore: switch (json['priority_score']) {
        final num value => value.toDouble(),
        final String value => double.parse(value),
        _ => null,
      },
      needsRoadReview: _field<bool>(json, 'needs_road_review'),
    ),
    'confirmed' => ConfirmedReport(
      id: id,
      status: status,
      severity: severity,
      address: address,
      confirmations: confirmations,
      createdAt: createdAt,
      confirmedAt: DateTime.parse(_field<String>(json, 'confirmed_at')),
    ),
    final other => throw FormatException('Relación desconocida: $other'),
  };
}

Map<String, dynamic> _map(Object? value) {
  if (value is Map<String, dynamic>) return value;
  throw const FormatException('Se esperaba un objeto JSON');
}

T _field<T>(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is T) return value;
  throw FormatException('Campo inválido: $key');
}
