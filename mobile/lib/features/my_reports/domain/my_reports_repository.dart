import 'dart:typed_data';

import 'my_report.dart';
import 'report_detail.dart';

/// Reportes del ciudadano. Los errores llegan como `ApiFailure`.
abstract interface class MyReportsRepository {
  /// Una página de los reportes creados o confirmados, del más reciente al más antiguo.
  Future<MyReportsPage> page({required int offset, int limit = myReportsPageSize});

  Future<ReportDetail> detail(String id);

  /// Miniatura JPEG de un reporte propio. Pasa por el cliente con sesión (propuesta 54).
  Future<Uint8List> thumbnail(String id);

  /// Foto JPEG de un reporte propio, para el detalle.
  Future<Uint8List> photo(String id);
}

/// Tamaño de página de «Mis reportes» (la API admite hasta 50).
const int myReportsPageSize = 20;
