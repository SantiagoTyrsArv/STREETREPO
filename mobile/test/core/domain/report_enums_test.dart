import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';

void main() {
  test('estados desde la API', () {
    expect(ReportStatus.fromApi('registrado'), ReportStatus.registered);
    expect(ReportStatus.fromApi('evaluado'), ReportStatus.evaluated);
    expect(ReportStatus.fromApi('priorizado'), ReportStatus.prioritized);
    expect(ReportStatus.fromApi('reparado'), ReportStatus.repaired);
    expect(() => ReportStatus.fromApi('otro'), throwsFormatException);
    expect(ReportStatus.prioritized.label, 'Priorizado');
  });

  test('severidad ida y vuelta', () {
    for (final severity in Severity.values) {
      expect(Severity.fromApi(severity.toApi()), severity);
    }
    expect(Severity.high.toApi(), 'alta');
    expect(Severity.low.label, 'Baja');
    expect(() => Severity.fromApi('grave'), throwsFormatException);
  });
}
