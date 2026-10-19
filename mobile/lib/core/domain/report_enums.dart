/// Estado del reporte tal como lo devuelve la API (guía 2.4). La app solo lo muestra.
enum ReportStatus {
  registered('registrado', 'Registrado'),
  evaluated('evaluado', 'Evaluado'),
  prioritized('priorizado', 'Priorizado'),
  repaired('reparado', 'Reparado');

  const ReportStatus(this.apiValue, this.label);

  final String apiValue;
  final String label;

  static ReportStatus fromApi(String value) => values.firstWhere(
    (status) => status.apiValue == value,
    orElse: () => throw FormatException('Estado desconocido: $value'),
  );
}

/// Severidad declarada por el ciudadano (guía 2.2).
enum Severity {
  low('baja', 'Baja'),
  medium('media', 'Media'),
  high('alta', 'Alta');

  const Severity(this._apiValue, this.label);

  final String _apiValue;
  final String label;

  String toApi() => _apiValue;

  static Severity fromApi(String value) => values.firstWhere(
    (severity) => severity._apiValue == value,
    orElse: () => throw FormatException('Severidad desconocida: $value'),
  );
}
