import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format/formatters.dart';
import '../../../core/network/api_error.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/primary_button.dart';
import '../../../core/widgets/state_views.dart';
import '../../../core/widgets/status_chip.dart';
import '../application/my_reports_controller.dart';
import '../domain/my_report.dart';
import 'report_thumbnail.dart';

/// Mis reportes (Figma `6:62`) con sus estados Cargando (`16:244`), Vacío (`16:295`) y Error
/// (`16:327`). Incluye los reportes que el ciudadano confirmó, marcados «Lo confirmaste».
class MyReportsScreen extends ConsumerStatefulWidget {
  const MyReportsScreen({super.key, this.now});

  /// Hora para «hace 3 días»; las pruebas la fijan.
  final DateTime? now;

  @override
  ConsumerState<MyReportsScreen> createState() => _MyReportsScreenState();
}

class _MyReportsScreenState extends ConsumerState<MyReportsScreen> {
  MyReportsFilter _filter = MyReportsFilter.all;

  Future<void> _refresh() async {
    final failure = await ref.read(myReportsProvider.notifier).refresh();
    if (failure != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(failure.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final reports = ref.watch(myReportsProvider);
    final theme = Theme.of(context);
    return SafeArea(
      bottom: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 28, 20, 0),
            child: Semantics(
              header: true,
              child: Text(
                'Mis reportes',
                style: theme.textTheme.headlineMedium?.copyWith(fontSize: 28),
              ),
            ),
          ),
          Expanded(
            child: switch (reports) {
              AsyncData(:final value) when value.items.isEmpty => EmptyView(
                glyph: '+',
                title: 'Aún no has reportado daños',
                message:
                    'Cuando envíes un reporte, aquí verás su estado: Registrado, Evaluado, '
                    'Priorizado o Reparado.',
                action: PrimaryButton(
                  label: 'Reportar un daño',
                  onPressed: () => context.push(AppRoutes.newReport),
                ),
              ),
              AsyncData(:final value) => _ReportList(
                state: value,
                filter: _filter,
                now: widget.now ?? DateTime.now().toUtc(),
                onFilter: (filter) => setState(() => _filter = filter),
                onRefresh: _refresh,
              ),
              AsyncError(:final error) => ErrorView(
                title: 'No pudimos cargar tus reportes',
                message: error is NetworkFailure
                    ? error.message
                    : 'Ocurrió un problema al consultar el servidor. Inténtalo de nuevo en un '
                          'momento.',
                onRetry: ref.read(myReportsProvider.notifier).retry,
              ),
              _ => const _LoadingList(),
            },
          ),
        ],
      ),
    );
  }
}

class _ReportList extends ConsumerWidget {
  const _ReportList({
    required this.state,
    required this.filter,
    required this.now,
    required this.onFilter,
    required this.onRefresh,
  });

  final MyReportsState state;
  final MyReportsFilter filter;
  final DateTime now;
  final ValueChanged<MyReportsFilter> onFilter;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final visible = state.items.where(filter.accepts).toList();
    final failure = state.loadMoreFailure;
    return RefreshIndicator(
      color: AppTokens.ink,
      onRefresh: onRefresh,
      child: NotificationListener<ScrollNotification>(
        // Al acercarse al final se pide la página siguiente.
        onNotification: (notification) {
          if (notification.metrics.extentAfter < 300) {
            ref.read(myReportsProvider.notifier).loadMore();
          }
          return false;
        },
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 14, 20, 24),
          children: [
            _Filters(selected: filter, onSelected: onFilter),
            const SizedBox(height: 16),
            if (visible.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Text(
                  filter == MyReportsFilter.repaired
                      ? 'Ninguno de tus reportes está reparado todavía.'
                      : 'No tienes reportes en proceso.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 15, color: AppTokens.textSecondary),
                ),
              ),
            for (final report in visible) ...[
              _ReportCard(report: report, now: now),
              const SizedBox(height: 12),
            ],
            if (state.loadingMore)
              const Padding(
                padding: EdgeInsets.all(12),
                child: Center(
                  child: CircularProgressIndicator(
                    color: AppTokens.ink,
                    semanticsLabel: 'Cargando más reportes',
                  ),
                ),
              )
            else if (failure != null)
              Column(
                children: [
                  Text(
                    'No pudimos cargar más reportes. ${failure.message}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 13, color: AppTokens.textSecondary),
                  ),
                  TextButton(
                    onPressed: ref.read(myReportsProvider.notifier).loadMore,
                    style: TextButton.styleFrom(
                      foregroundColor: AppTokens.link,
                      minimumSize: const Size(0, AppTokens.minTouchTarget),
                    ),
                    child: const Text('Reintentar'),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _Filters extends StatelessWidget {
  const _Filters({required this.selected, required this.onSelected});

  final MyReportsFilter selected;
  final ValueChanged<MyReportsFilter> onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        for (final filter in MyReportsFilter.values)
          Semantics(
            button: true,
            selected: filter == selected,
            label: 'Filtro ${filter.label}',
            excludeSemantics: true,
            child: Material(
              color: filter == selected ? AppTokens.ink : AppTokens.sand,
              shape: const StadiumBorder(),
              child: InkWell(
                customBorder: const StadiumBorder(),
                onTap: () => onSelected(filter),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: AppTokens.minTouchTarget),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Center(
                      widthFactor: 1,
                      child: Text(
                        filter.label,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: filter == selected ? AppTokens.surface : AppTokens.ink,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _ReportCard extends StatelessWidget {
  const _ReportCard({required this.report, required this.now});

  final MyReport report;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final (String title, String subtitle) = switch (report) {
      OwnReport(:final description?) when description.trim().isNotEmpty => (
        description,
        report.address,
      ),
      OwnReport() => (report.address, 'Severidad ${report.severity.label.toLowerCase()}'),
      ConfirmedReport() => ('Lo confirmaste', report.address),
    };
    return Material(
      color: AppTokens.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppTokens.cardRadius),
        side: const BorderSide(color: AppTokens.line),
      ),
      child: InkWell(
        customBorder: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppTokens.cardRadius),
        ),
        onTap: () => context.push(AppRoutes.reportDetailOf(report.id)),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              ReportThumbnail(reportId: report.id, hasPhoto: report is OwnReport),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        StatusChip(report.status),
                        Text(
                          formatRelative(report.relatedAt, now),
                          style: const TextStyle(fontSize: 12, color: AppTokens.textSecondary),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: const TextStyle(fontSize: 13, color: AppTokens.textSecondary),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Esqueletos del Figma (`16:244`) mientras llega la primera página.
class _LoadingList extends StatelessWidget {
  const _LoadingList();

  @override
  Widget build(BuildContext context) {
    Widget bar(double width, double height) => Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: AppTokens.sand,
        borderRadius: BorderRadius.circular(height / 2),
      ),
    );
    return Semantics(
      label: 'Cargando tus reportes',
      excludeSemantics: true,
      child: ListView(
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 24),
        children: [
          for (var i = 0; i < 4; i++) ...[
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppTokens.surface,
                border: Border.all(color: AppTokens.line),
                borderRadius: BorderRadius.circular(AppTokens.cardRadius),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 64,
                    height: 64,
                    decoration: BoxDecoration(
                      color: AppTokens.sand,
                      borderRadius: BorderRadius.circular(AppTokens.fieldRadius),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        bar(170, 14),
                        const SizedBox(height: 10),
                        bar(120, 12),
                        const SizedBox(height: 10),
                        bar(80, 20),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
        ],
      ),
    );
  }
}
