import 'package:flutter/material.dart';

import '../domain/report_enums.dart';
import '../theme/app_tokens.dart';
import 'status_chip.dart';

/// Color de cada severidad (guía 10.1); el texto acompaña siempre al color.
Color severityColor(Severity severity) => switch (severity) {
  Severity.low => AppTokens.severityLow,
  Severity.medium => AppTokens.severityMedium,
  Severity.high => AppTokens.severityHigh,
};

class SeverityChip extends StatelessWidget {
  const SeverityChip(this.severity, {super.key});

  final Severity severity;

  @override
  Widget build(BuildContext context) {
    final color = severityColor(severity);
    return Semantics(
      label: 'Severidad: ${severity.label}',
      excludeSemantics: true,
      child: ChipLabel(
        label: severity.label,
        background: color.withValues(alpha: 0.12),
        foreground: color,
      ),
    );
  }
}
