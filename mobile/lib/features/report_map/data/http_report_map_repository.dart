import 'package:dio/dio.dart';

import '../../../core/domain/report_enums.dart';
import '../../../core/network/api_error.dart';
import '../domain/map_report.dart';
import '../domain/report_map_repository.dart';

/// `GET /reports?bbox=…`. Traduce los errores a `ApiFailure`; una respuesta con otra forma
/// es `UnexpectedFailure`.
class HttpReportMapRepository implements ReportMapRepository {
  HttpReportMapRepository(this._dio);

  final Dio _dio;

  @override
  Future<MapReportsPage> listInArea(MapArea area, {ReportStatus? status}) async {
    try {
      final response = await _dio.get<Object?>(
        '/reports',
        queryParameters: {'bbox': area.toBbox(), 'status': ?status?.apiValue},
      );
      final json = _object(response.data);
      final items = json['items'];
      if (items is! List) throw const FormatException('items no es una lista');
      return MapReportsPage(
        items: [for (final item in items) _report(_object(item))],
        truncated: _field<bool>(json, 'truncated'),
      );
    } on DioException catch (e) {
      throw ApiFailure.fromDioException(e);
    } on FormatException {
      throw const UnexpectedFailure();
    }
  }

  static MapReport _report(Map<String, dynamic> json) {
    final location = _object(json['location']);
    return MapReport(
      id: _field<String>(json, 'id'),
      latitude: _field<num>(location, 'latitude').toDouble(),
      longitude: _field<num>(location, 'longitude').toDouble(),
      status: ReportStatus.fromApi(_field<String>(json, 'status')),
      severity: Severity.fromApi(_field<String>(json, 'severity')),
      address: _field<String>(json, 'address'),
      confirmations: _field<int>(json, 'confirmations'),
      createdAt: DateTime.parse(_field<String>(json, 'created_at')),
      isMine: _field<bool>(json, 'is_mine'),
      confirmedByMe: _field<bool>(json, 'confirmed_by_me'),
    );
  }

  static Map<String, dynamic> _object(Object? value) {
    if (value is Map<String, dynamic>) return value;
    throw const FormatException('Se esperaba un objeto JSON');
  }

  static T _field<T>(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is T) return value;
    throw FormatException('Campo inválido: $key');
  }
}
