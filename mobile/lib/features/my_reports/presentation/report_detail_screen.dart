import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/domain/report_enums.dart';
import '../../../core/format/formatters.dart';
import '../../../core/network/api_error.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/severity_chip.dart';
import '../../../core/widgets/state_views.dart';
import '../../../core/widgets/status_chip.dart';
import '../application/my_reports_controller.dart';
import '../domain/my_report.dart';
import '../domain/report_detail.dart';

/// Detalle del reporte (Figma `6:3`). La vista completa (autor o administrador) muestra la
/// foto, la urgencia U y «Revisar vía»; quien solo lo confirmó ve la vista limitada, sin
/// foto, urgencia ni observaciones (decisión 49).
///
/// Diferencias con el Figma: no hay botón «Confirmar este daño», porque al detalle solo
/// llegan el autor (que no puede confirmar el suyo, propuesta 48) y quien ya lo confirmó; y
/// el historial muestra la fecha y la observación del servidor, sin el autor del cambio.
class ReportDetailScreen extends ConsumerWidget {
  const ReportDetailScreen({required this.reportId, super.key, this.now});

  final String reportId;

  /// Hora para «reportado hace 3 días»; las pruebas la fijan.
  final DateTime? now;

  void _back(BuildContext context) =>
      context.canPop() ? context.pop() : context.go(AppRoutes.myReports);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(reportDetailProvider(reportId));
    return Scaffold(
      body: switch (detail) {
        AsyncData(:final value) => _DetailBody(
          detail: value,
          now: now ?? DateTime.now().toUtc(),
          onBack: () => _back(context),
        ),
        AsyncError(:final error) => SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.all(12),
                child: _RoundBackButton(onPressed: () => _back(context)),
              ),
              Expanded(
                child: ErrorView(
                  title: 'No pudimos abrir el reporte',
                  message: error is ApiFailure ? error.message : const UnexpectedFailure().message,
                  onRetry: () => ref.invalidate(reportDetailProvider(reportId)),
                ),
              ),
            ],
          ),
        ),
        _ => const LoadingView(label: 'Cargando el reporte…'),
      },
    );
  }
}

class _DetailBody extends StatelessWidget {
  const _DetailBody({required this.detail, required this.now, required this.onBack});

  final ReportDetail detail;
  final DateTime now;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    final report = detail.report;
    final own = report is OwnReport && detail.isFullView ? report : null;
    final description = own?.description?.trim() ?? '';
    final theme = Theme.of(context);
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight),
          child: IntrinsicHeight(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _PhotoHeader(reportId: report.id, hasPhoto: own != null, onBack: onBack),
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 8,
                        runSpacing: 6,
                        children: [
                          StatusChip(report.status),
                          SeverityChip(report.severity),
                          if (own?.needsRoadReview ?? false)
                            Semantics(
                              label: 'Revisar vía: no hay una vía registrada a 30 m',
                              excludeSemantics: true,
                              child: const ChipLabel(
                                label: 'Revisar vía',
                                background: AppTokens.amberSoft,
                                foreground: AppTokens.prioritizedChipText,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Semantics(
                        header: true,
                        child: Text(
                          description.isNotEmpty ? description : report.address,
                          style: theme.textTheme.headlineMedium?.copyWith(
                            fontSize: 24,
                            height: 28 / 24,
                          ),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: const EdgeInsets.only(top: 2),
                            child: ExcludeSemantics(
                              child: SvgPicture.asset('assets/icons/pin_tiny.svg'),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              '${report.address} · reportado '
                              '${_withArticle(formatRelative(report.createdAt, now))}',
                              style: const TextStyle(fontSize: 14, color: AppTokens.cardText),
                            ),
                          ),
                        ],
                      ),
                      if (own?.priorityScore case final score?) ...[
                        const SizedBox(height: 16),
                        _UrgencyCard(score: score),
                      ],
                      const SizedBox(height: 16),
                      _HistoryCard(detail: detail),
                    ],
                  ),
                ),
                const Spacer(),
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
                  child: SafeArea(top: false, child: _Confirmations(detail: detail)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// «hace 3 días», «hoy»; una fecha va con artículo: «el 13 oct».
String _withArticle(String relative) =>
    RegExp(r'^\d').hasMatch(relative) ? 'el $relative' : relative;

class _PhotoHeader extends ConsumerWidget {
  const _PhotoHeader({required this.reportId, required this.hasPhoto, required this.onBack});

  final String reportId;
  final bool hasPhoto;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final photo = hasPhoto ? ref.watch(reportPhotoProvider(reportId)) : null;
    final bytes = photo?.value;
    final placeholder = switch (photo) {
      null => 'Solo quien lo reportó ve la foto',
      AsyncError() => 'No pudimos cargar la foto',
      _ => 'Foto del daño',
    };
    final top = MediaQuery.paddingOf(context).top;
    return SizedBox(
      height: 210 + top,
      width: double.infinity,
      child: Stack(
        fit: StackFit.expand,
        children: [
          ColoredBox(
            color: AppTokens.photoPlaceholder,
            child: bytes != null
                ? Image.memory(
                    bytes,
                    fit: BoxFit.cover,
                    gaplessPlayback: true,
                    semanticLabel: 'Foto del daño',
                  )
                : Padding(
                    padding: EdgeInsets.only(top: top),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        ExcludeSemantics(child: SvgPicture.asset('assets/icons/camera_detail.svg')),
                        const SizedBox(height: 6),
                        Text(
                          placeholder,
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 13, color: AppTokens.onDarkMuted),
                        ),
                      ],
                    ),
                  ),
          ),
          Positioned(
            left: 12,
            top: top + 12,
            child: _RoundBackButton(onPressed: onBack),
          ),
        ],
      ),
    );
  }
}

class _RoundBackButton extends StatelessWidget {
  const _RoundBackButton({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Volver',
      excludeSemantics: true,
      child: Material(
        color: AppTokens.surface,
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: onPressed,
          child: SizedBox.square(
            dimension: AppTokens.minTouchTarget,
            child: Center(child: SvgPicture.asset('assets/icons/back_small.svg')),
          ),
        ),
      ),
    );
  }
}

class _UrgencyCard extends StatelessWidget {
  const _UrgencyCard({required this.score});

  final double score;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Urgencia ${formatScore(score)} de 10',
      excludeSemantics: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppTokens.surface,
          border: Border.all(color: AppTokens.line),
          borderRadius: BorderRadius.circular(AppTokens.cardRadius),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            const Expanded(child: _SectionLabel('Urgencia')),
            Text(
              formatScore(score),
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 24),
            ),
            const SizedBox(width: 4),
            const Padding(
              padding: EdgeInsets.only(bottom: 4),
              child: Text('de 10', style: TextStyle(fontSize: 13, color: AppTokens.textSecondary)),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text.toUpperCase(),
      style: const TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: AppTokens.textSecondary,
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.detail});

  final ReportDetail detail;

  static Color _statusColor(ReportStatus status) => switch (status) {
    ReportStatus.registered => AppTokens.registeredFg,
    ReportStatus.evaluated => AppTokens.evaluatedFg,
    ReportStatus.prioritized => AppTokens.prioritizedFg,
    ReportStatus.repaired => AppTokens.repairedFg,
  };

  @override
  Widget build(BuildContext context) {
    final current = detail.report.status;
    // Lo más reciente arriba, como en el Figma; después, los estados que faltan.
    final entries = detail.history.reversed.toList();
    final pending = ReportStatus.values.where((s) => s.index > current.index);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppTokens.surface,
        border: Border.all(color: AppTokens.line),
        borderRadius: BorderRadius.circular(AppTokens.cardRadius),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _SectionLabel('Historial'),
          for (final entry in entries) ...[
            const SizedBox(height: 12),
            _HistoryRow(
              status: entry.status,
              color: _statusColor(entry.status),
              subtitle: _subtitle(entry),
            ),
          ],
          for (final status in pending) ...[
            const SizedBox(height: 12),
            _HistoryRow(status: status, subtitle: 'Pendiente'),
          ],
        ],
      ),
    );
  }

  String _subtitle(HistoryEntry entry) {
    final date = formatShortDate(entry.changedAt);
    final note = entry.note?.trim() ?? '';
    if (note.isNotEmpty) return '$date · $note';
    final isCreation = identical(entry, detail.history.firstOrNull);
    if (detail.isMine && isCreation) return '$date · tú enviaste este reporte';
    return date;
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.status, required this.subtitle, this.color});

  final ReportStatus status;
  final String subtitle;

  /// Color del estado alcanzado; null = pendiente (círculo vacío).
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final reached = color != null;
    return Semantics(
      label: '${status.label}. $subtitle',
      excludeSemantics: true,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: color,
                border: reached ? null : Border.all(color: AppTokens.inputBorder, width: 2),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  status.label,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: reached ? FontWeight.w700 : FontWeight.w600,
                    color: reached ? AppTokens.ink : AppTokens.textSecondary,
                  ),
                ),
                const SizedBox(height: 1),
                Text(
                  subtitle,
                  style: const TextStyle(fontSize: 12, color: AppTokens.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Confirmations extends StatelessWidget {
  const _Confirmations({required this.detail});

  final ReportDetail detail;

  @override
  Widget build(BuildContext context) {
    final report = detail.report;
    final count = switch (report.confirmations) {
      0 => 'Nadie ha confirmado este daño aún',
      1 => '1 vecino confirmó este daño',
      final n => '$n vecinos confirmaron este daño',
    };
    final text = report is ConfirmedReport
        ? 'Lo confirmaste el ${formatShortDate(report.confirmedAt)} · $count'
        : count;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ExcludeSemantics(child: SvgPicture.asset('assets/icons/users.svg')),
        const SizedBox(width: 8),
        Expanded(
          child: Text(text, style: const TextStyle(fontSize: 13, color: AppTokens.cardText)),
        ),
      ],
    );
  }
}
