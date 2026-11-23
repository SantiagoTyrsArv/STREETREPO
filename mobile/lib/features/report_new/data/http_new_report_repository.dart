import 'package:dio/dio.dart';

import '../../../core/domain/report_enums.dart';
import '../../../core/network/api_error.dart';
import '../domain/nearby_report.dart';
import '../domain/new_report_repository.dart';
import '../domain/report_draft.dart';

/// Rutas de reportes de la API: `GET /reports/nearby`, `POST /reports` (multipart) y
/// `POST /reports/{id}/confirmations`. Traduce los errores a `ApiFailure`; una respuesta con
/// otra forma es `UnexpectedFailure`.
class HttpNewReportRepository implements NewReportRepository {
  HttpNewReportRepository(this._dio);

  final Dio _dio;

  @override
  Future<NearbyResult> nearby(GeoFix fix) => _call(() async {
    final json = _json(
      await _dio.get<Object?>(
        '/reports/nearby',
        queryParameters: {'longitude': fix.longitude, 'latitude': fix.latitude},
      ),
    );
    return NearbyResult(
      candidates: parseNearbyItems(json['items']),
      warningId: parseWarningId(json),
    );
  });

  @override
  Future<CreatedReport> create(
    ReportDraft draft, {
    required String idempotencyKey,
    required bool createAnyway,
    String? duplicateWarningId,
  }) => _call(() async {
    final photo = draft.photo;
    final fix = draft.fix;
    final severity = draft.severity;
    if (photo == null || fix == null || severity == null) {
      throw StateError('El borrador está incompleto');
    }
    final form = FormData.fromMap({
      'photo': MultipartFile.fromBytes(
        photo.jpegBytes,
        filename: 'foto.jpg',
        contentType: DioMediaType('image', 'jpeg'),
      ),
      // La API usa punto decimal.
      'longitude': fix.longitude.toString(),
      'latitude': fix.latitude.toString(),
      'severity': severity.toApi(),
      if (draft.description.trim().isNotEmpty) 'description': draft.description.trim(),
      'create_anyway': createAnyway.toString(),
      'duplicate_warning_id': ?duplicateWarningId,
    });
    final json = _json(
      await _dio.post<Object?>(
        '/reports',
        data: form,
        options: Options(headers: {'Idempotency-Key': idempotencyKey}),
      ),
    );
    return CreatedReport(
      id: _field<String>(json, 'id'),
      status: ReportStatus.fromApi(_field<String>(json, 'status')),
      address: _field<String>(json, 'address'),
    );
  });

  @override
  Future<int> confirm(String reportId, GeoFix fix, {String? duplicateWarningId}) => _call(() async {
    final json = _json(
      await _dio.post<Object?>(
        '/reports/$reportId/confirmations',
        data: {
          'longitude': fix.longitude,
          'latitude': fix.latitude,
          'duplicate_warning_id': ?duplicateWarningId,
        },
      ),
    );
    return _field<int>(json, 'confirmations');
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

  static Map<String, dynamic> _json(Response<Object?> response) {
    final body = response.data;
    if (body is Map<String, dynamic>) return body;
    throw const FormatException('La respuesta no es un objeto JSON');
  }
}

/// Candidatos de `nearby` o de `details.items` del 409 `REPORT_DUPLICATE_NEARBY`. Lanza
/// [FormatException] si la forma no es la esperada.
List<NearbyReport> parseNearbyItems(Object? items) {
  if (items is! List<Object?>) throw const FormatException('Faltan los candidatos');
  return [
    for (final item in items)
      if (item is Map<String, dynamic>)
        NearbyReport(
          id: _field<String>(item, 'id'),
          distanceMeters: _field<num>(item, 'distance_m').toDouble(),
          status: ReportStatus.fromApi(_field<String>(item, 'status')),
          severity: Severity.fromApi(_field<String>(item, 'severity')),
          confirmations: _field<int>(item, 'confirmations'),
          address: _field<String>(item, 'address'),
          createdAt: DateTime.parse(_field<String>(item, 'created_at')),
          isMine: _field<bool>(item, 'is_mine'),
        )
      else
        throw const FormatException('Candidato inválido'),
  ];
}

/// `duplicate_warning_id` de `nearby` o de `details` del 409; `null` si no viene o no es texto
/// (una API anterior no lo envía).
String? parseWarningId(Map<String, dynamic> json) {
  final value = json['duplicate_warning_id'];
  return value is String ? value : null;
}

T _field<T>(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is T) return value;
  throw FormatException('Campo inválido: $key');
}
