import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format/formatters.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/app_back_button.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/notice_banner.dart';
import '../../../core/widgets/primary_button.dart';
import '../../../core/widgets/severity_chip.dart';
import '../../../core/widgets/status_chip.dart';
import '../application/submit_report_controller.dart';
import '../domain/nearby_report.dart';
import '../domain/submit_outcome.dart';
import 'submit_navigation.dart';

/// Posible duplicado (Figma `5:54`): reportes activos a 25 m. El ciudadano confirma uno
/// ajeno (HU-16) o envía el suyo de todos modos. Los propios llevan «Tu reporte» y no se
/// pueden confirmar (propuesta 48).
class DuplicateScreen extends ConsumerStatefulWidget {
  const DuplicateScreen({super.key, this.now});

  /// Hora para «reportado hace N días»; las pruebas la fijan.
  final DateTime? now;

  @override
  ConsumerState<DuplicateScreen> createState() => _DuplicateScreenState();
}

enum _Action { confirm, create }

class _DuplicateScreenState extends ConsumerState<DuplicateScreen> {
  /// Se leen una vez: al confirmar, el resultado del controlador cambia antes de navegar.
  late final List<NearbyReport> _candidates;
  NearbyReport? _selected;
  _Action? _running;
  SubmitFailed? _failure;

  @override
  void initState() {
    super.initState();
    final outcome = ref.read(submitReportProvider).outcome;
    _candidates = outcome is PossibleDuplicates ? outcome.candidates : const [];
    _selected = _confirmable.firstOrNull;
  }

  List<NearbyReport> get _confirmable => [
    for (final candidate in _candidates)
      if (!candidate.isMine) candidate,
  ];

  void _back() => context.canPop() ? context.pop() : context.go(AppRoutes.newReportSeverity);

  Future<void> _do(_Action action, Future<SubmitOutcome> Function() run) async {
    setState(() {
      _running = action;
      _failure = null;
    });
    final outcome = await run();
    if (!mounted) return;
    final shown = showSubmitOutcome(context, outcome);
    setState(() {
      _running = null;
      if (!shown) _failure = outcome as SubmitFailed;
    });
  }

  String _intro() {
    if (_candidates.length > 1) {
      return 'Encontramos ${_candidates.length} reportes activos a menos de 25 m de tu '
          'ubicación. Si alguno es el mismo daño, confírmalo en lugar de crear uno nuevo.';
    }
    final distance = _candidates.isEmpty ? 0 : _candidates.single.distanceMeters.round();
    if (_confirmable.isEmpty) {
      return 'Ya reportaste un daño a $distance m de tu ubicación. Si es otro daño, envía tu '
          'reporte.';
    }
    return 'Encontramos un reporte activo a $distance m de tu ubicación. Si es el mismo daño, '
        'confírmalo en lugar de crear uno nuevo.';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final now = widget.now ?? DateTime.now().toUtc();
    final selectable = _confirmable.length > 1;
    final failure = _failure;
    return Scaffold(
      body: SafeArea(
        child: FillScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            AppBackButton(onPressed: _back),
            const SizedBox(height: 4),
            Semantics(
              header: true,
              child: Text(
                _candidates.length > 1 ? 'Ya existen reportes cerca' : 'Ya existe un reporte cerca',
                style: theme.textTheme.headlineMedium?.copyWith(fontSize: 26, height: 28 / 26),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _intro(),
              style: const TextStyle(fontSize: 14, height: 20 / 14, color: AppTokens.textSecondary),
            ),
            const SizedBox(height: 16),
            const _ProximityMap(),
            for (final candidate in _candidates) ...[
              const SizedBox(height: 14),
              _CandidateCard(
                report: candidate,
                now: now,
                showDistance: _candidates.length > 1,
                selected: selectable && identical(candidate, _selected),
                onTap: selectable && !candidate.isMine && _running == null
                    ? () => setState(() => _selected = candidate)
                    : null,
              ),
            ],
            const Spacer(),
            const SizedBox(height: 24),
            if (failure != null) ...[
              NoticeBanner(message: failure.message),
              const SizedBox(height: 12),
            ],
            if (_selected case final target?) ...[
              PrimaryButton(
                label: 'Es el mismo daño: confirmarlo',
                variant: ButtonVariant.dark,
                loading: _running == _Action.confirm,
                onPressed: _running == null
                    ? () => _do(
                        _Action.confirm,
                        () => ref.read(submitReportProvider.notifier).confirm(target),
                      )
                    : null,
              ),
              const SizedBox(height: 10),
            ],
            PrimaryButton(
              label: 'Es otro daño: enviar mi reporte',
              variant: _selected == null ? ButtonVariant.dark : ButtonVariant.secondary,
              loading: _running == _Action.create,
              onPressed: _running == null
                  ? () => _do(_Action.create, ref.read(submitReportProvider.notifier).createAnyway)
                  : null,
            ),
          ],
        ),
      ),
    );
  }
}

/// Ilustración del Figma con la leyenda; el mapa real llega con la pantalla de mapa.
class _ProximityMap extends StatelessWidget {
  const _ProximityMap();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppTokens.surface,
        border: Border.all(color: AppTokens.line),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: 170,
            width: double.infinity,
            child: ClipRect(
              child: ExcludeSemantics(
                child: OverflowBox(
                  maxWidth: double.infinity,
                  child: SvgPicture.asset('assets/icons/duplicate_map.svg'),
                ),
              ),
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Wrap(
              spacing: 10,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                _LegendItem(color: AppTokens.link, label: 'Tu ubicación'),
                _LegendItem(color: AppTokens.registeredFg, label: 'Reporte existente'),
                Text('Radio de 25 m', style: TextStyle(fontSize: 12, color: AppTokens.cardText)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 12, color: AppTokens.cardText)),
      ],
    );
  }
}

class _CandidateCard extends StatelessWidget {
  const _CandidateCard({
    required this.report,
    required this.now,
    required this.showDistance,
    required this.selected,
    required this.onTap,
  });

  final NearbyReport report;
  final DateTime now;
  final bool showDistance;
  final bool selected;
  final VoidCallback? onTap;

  String _confirmations() => switch (report.confirmations) {
    0 => 'Nadie lo ha confirmado aún',
    1 => '1 vecino lo ha confirmado',
    final n => '$n vecinos lo han confirmado',
  };

  String _age() {
    final relative = formatRelative(report.createdAt, now);
    // «hace 5 días», «hoy»; una fecha va con artículo: «el 13 oct».
    return RegExp(r'^\d').hasMatch(relative) ? 'reportado el $relative' : 'reportado $relative';
  }

  @override
  Widget build(BuildContext context) {
    final details = [
      if (showDistance) 'A ${report.distanceMeters.round()} m',
      _confirmations(),
      _age(),
    ].join(' · ');
    return Semantics(
      container: true,
      selected: onTap == null ? null : selected,
      button: onTap != null,
      child: Material(
        color: AppTokens.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppTokens.cardRadius),
          side: selected
              ? const BorderSide(color: AppTokens.ink, width: 2)
              : const BorderSide(color: AppTokens.line),
        ),
        child: InkWell(
          onTap: onTap,
          customBorder: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTokens.cardRadius),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    if (report.isMine)
                      Semantics(
                        label: 'Tu reporte',
                        excludeSemantics: true,
                        child: const ChipLabel(
                          label: 'Tu reporte',
                          background: AppTokens.ink,
                          foreground: AppTokens.surface,
                        ),
                      ),
                    StatusChip(report.status),
                    SeverityChip(report.severity),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  report.address,
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ExcludeSemantics(child: SvgPicture.asset('assets/icons/users.svg')),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        details,
                        style: const TextStyle(fontSize: 13, color: AppTokens.cardText),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
