import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/domain/report_enums.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/primary_button.dart';
import '../application/submit_report_controller.dart';
import '../domain/submit_outcome.dart';

/// Reporte enviado (Figma `5:102`), y la misma pantalla con «Confirmación registrada» tras
/// confirmar un duplicado. Muestra el estado y la dirección que respondió el servidor.
///
/// Diferencias con el Figma: el MVP no envía avisos, así que el texto invita a seguir el
/// reporte en «Mis reportes» en vez de prometer un aviso; y «Volver al mapa» lleva a
/// «Mis reportes» hasta que exista el mapa.
class ReportSentScreen extends ConsumerStatefulWidget {
  const ReportSentScreen({super.key});

  @override
  ConsumerState<ReportSentScreen> createState() => _ReportSentScreenState();
}

class _ReportSentScreenState extends ConsumerState<ReportSentScreen> {
  late final SubmitOutcome? _outcome;

  @override
  void initState() {
    super.initState();
    _outcome = ref.read(submitReportProvider).outcome;
    if (_outcome is! Sent && _outcome is! Confirmed) {
      // Sin un envío terminado (p. ej. la app se reabrió aquí) no hay nada que mostrar.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) context.go(AppRoutes.myReports);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final (
      String id,
      String title,
      String body,
      ReportStatus status,
      String address,
    ) = switch (_outcome) {
      Sent(:final report) => (
        report.id,
        '¡Gracias! Tu reporte quedó registrado',
        'La Secretaría de Infraestructura lo evaluará y le asignará una prioridad. Puedes '
            'seguir su estado en Mis reportes.',
        report.status,
        report.address,
      ),
      Confirmed(:final report, :final confirmations) => (
        report.id,
        'Confirmación registrada',
        confirmations == 1
            ? 'Sumaste tu confirmación a este reporte. Ayuda a la Secretaría a ordenar la '
                  'atención de los daños.'
            : 'Sumaste tu confirmación a este reporte, que ya tiene $confirmations '
                  'confirmaciones. Ayuda a la Secretaría a ordenar la atención de los daños.',
        report.status,
        report.address,
      ),
      _ => ('', '', '', ReportStatus.registered, ''),
    };
    if (id.isEmpty) return const Scaffold(body: SizedBox.shrink());
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: FillScrollView(
          padding: const EdgeInsets.fromLTRB(24, 96, 24, 32),
          children: [
            const Center(child: _SuccessBadge()),
            const SizedBox(height: 28),
            SizedBox(
              width: double.infinity,
              child: Semantics(
                header: true,
                child: Text(
                  title,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineMedium?.copyWith(fontSize: 30, height: 32 / 30),
                ),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: Text(
                body,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 15,
                  height: 22 / 15,
                  color: AppTokens.textSecondary,
                ),
              ),
            ),
            const SizedBox(height: 28),
            _StatusCard(status: status, address: address),
            const Spacer(),
            const SizedBox(height: 24),
            PrimaryButton(
              label: _outcome is Confirmed ? 'Ver el reporte' : 'Ver mi reporte',
              variant: ButtonVariant.dark,
              onPressed: () => context
                ..go(AppRoutes.myReports)
                ..push(AppRoutes.reportDetailOf(id)),
            ),
            const SizedBox(height: 10),
            PrimaryButton(
              label: 'Ir a Mis reportes',
              variant: ButtonVariant.secondary,
              onPressed: () => context.go(AppRoutes.myReports),
            ),
          ],
        ),
      ),
    );
  }
}

class _SuccessBadge extends StatelessWidget {
  const _SuccessBadge();

  @override
  Widget build(BuildContext context) {
    return ExcludeSemantics(
      child: Container(
        width: 96,
        height: 96,
        alignment: Alignment.center,
        decoration: const BoxDecoration(color: AppTokens.repairedChip, shape: BoxShape.circle),
        child: Container(
          width: 64,
          height: 64,
          alignment: Alignment.center,
          decoration: const BoxDecoration(color: AppTokens.repairedFg, shape: BoxShape.circle),
          child: SvgPicture.asset('assets/icons/check_large.svg'),
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.status, required this.address});

  final ReportStatus status;
  final String address;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTokens.surface,
        border: Border.all(color: AppTokens.line),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'ESTADO DEL REPORTE',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: AppTokens.textSecondary,
            ),
          ),
          const SizedBox(height: 12),
          Semantics(
            label: 'Estado actual: ${status.label}',
            excludeSemantics: true,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final step in ReportStatus.values)
                  Expanded(
                    child: _Step(step: step, reached: step.index <= status.index),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              ExcludeSemantics(child: SvgPicture.asset('assets/icons/pin_small.svg')),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  address,
                  style: const TextStyle(fontSize: 13, color: AppTokens.cardText),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step({required this.step, required this.reached});

  final ReportStatus step;
  final bool reached;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 18,
          height: 18,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: reached ? AppTokens.ink : null,
            border: reached ? null : Border.all(color: AppTokens.inputBorder, width: 2),
          ),
        ),
        const SizedBox(height: 6),
        Text(
          step.label,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 12,
            fontWeight: reached ? FontWeight.w700 : FontWeight.w500,
            color: reached ? AppTokens.ink : AppTokens.textSecondary,
          ),
        ),
      ],
    );
  }
}
