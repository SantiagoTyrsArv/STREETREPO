import 'package:flutter/material.dart';

import '../domain/report_enums.dart';
import '../theme/app_tokens.dart';

/// Chip de estado del Figma: siempre con texto, nunca solo color (guía 10.3).
class StatusChip extends StatelessWidget {
  const StatusChip(this.status, {super.key});

  final ReportStatus status;

  @override
  Widget build(BuildContext context) {
    final (background, foreground) = switch (status) {
      ReportStatus.registered => (AppTokens.registeredChip, AppTokens.registeredChipText),
      ReportStatus.evaluated => (AppTokens.evaluatedChip, AppTokens.evaluatedChipText),
      ReportStatus.prioritized => (AppTokens.prioritizedChip, AppTokens.prioritizedChipText),
      ReportStatus.repaired => (AppTokens.repairedChip, AppTokens.repairedChipText),
    };
    return Semantics(
      label: 'Estado: ${status.label}',
      excludeSemantics: true,
      child: _Chip(label: status.label, background: background, foreground: foreground),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.background, required this.foreground});

  final String label;
  final Color background;
  final Color foreground;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppTokens.chipRadius),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        child: Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(color: foreground),
        ),
      ),
    );
  }
}

/// Mismo aspecto que el chip de estado, para reutilizarlo en severidad.
class ChipLabel extends StatelessWidget {
  const ChipLabel({
    required this.label,
    required this.background,
    required this.foreground,
    super.key,
  });

  final String label;
  final Color background;
  final Color foreground;

  @override
  Widget build(BuildContext context) =>
      _Chip(label: label, background: background, foreground: foreground);
}
