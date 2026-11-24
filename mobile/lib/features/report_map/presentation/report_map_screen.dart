import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';

import '../../../core/config/app_config.dart';
import '../../../core/domain/report_enums.dart';
import '../../../core/format/formatters.dart';
import '../../../core/network/api_error.dart';
import '../../../core/platform/url_opener.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/primary_button.dart';
import '../../../core/widgets/severity_chip.dart';
import '../../../core/widgets/status_chip.dart';
import '../application/report_map_controller.dart';
import '../domain/map_report.dart';

/// Centro de Pasto: donde abre el mapa.
const LatLng _pastoCenter = LatLng(1.2136, -77.2811);
const double _initialZoom = 15;
const double _minZoom = 11;
const double _maxZoom = 19;

/// Espera tras el último movimiento del mapa antes de pedir los reportes del área nueva.
const Duration _moveDebounce = Duration(milliseconds: 400);

/// Identifica la app ante el proveedor de teselas (política de uso de OpenStreetMap).
const String _userAgentPackage = 'co.edu.ucc.street_repo';

/// Capa de teselas del mapa. Es un proveedor para poder cambiarla en las pruebas, que no
/// tienen red.
final mapTileLayerProvider = Provider<Widget>(
  (ref) => TileLayer(
    urlTemplate: ref.watch(appConfigProvider).tileUrlTemplate,
    userAgentPackageName: _userAgentPackage,
    maxNativeZoom: _maxZoom.toInt(),
  ),
);

Color _statusColor(ReportStatus status) => switch (status) {
  ReportStatus.registered => AppTokens.registeredFg,
  ReportStatus.evaluated => AppTokens.evaluatedFg,
  ReportStatus.prioritized => AppTokens.prioritizedFg,
  ReportStatus.repaired => AppTokens.repairedFg,
};

/// Mapa de reportes (Figma `4:2` y `16:359`): los reportes del área visible, con filtro por
/// estado y la ficha del reporte elegido. Las ubicaciones son las aproximadas que publica
/// la API. El buscador de direcciones del Figma no está en esta entrega.
class ReportMapScreen extends ConsumerStatefulWidget {
  const ReportMapScreen({super.key});

  @override
  ConsumerState<ReportMapScreen> createState() => _ReportMapScreenState();
}

class _ReportMapScreenState extends ConsumerState<ReportMapScreen> {
  final _map = MapController();
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _map.dispose();
    super.dispose();
  }

  MapArea _visibleArea() {
    final bounds = _map.camera.visibleBounds;
    return MapArea(west: bounds.west, south: bounds.south, east: bounds.east, north: bounds.north);
  }

  void _onReady() {
    // Al abrir la pestaña siempre se pide de nuevo: pudo entrar un reporte desde la última vez.
    ref.read(reportMapProvider.notifier).showArea(_visibleArea(), force: true);
  }

  void _onMoved() {
    _debounce?.cancel();
    _debounce = Timer(_moveDebounce, () {
      if (mounted) ref.read(reportMapProvider.notifier).showArea(_visibleArea());
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(reportMapProvider);
    final controller = ref.read(reportMapProvider.notifier);
    ref.listen(reportMapProvider.select((s) => s.confirmedNotice), (_, notice) {
      if (!notice) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Confirmación registrada.')));
      controller.noticeShown();
    });
    final selected = state.selected;
    return SafeArea(
      bottom: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 10),
            child: Semantics(
              header: true,
              child: Text(
                'Mapa de reportes',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 28),
              ),
            ),
          ),
          _Filters(selected: state.filter, onSelected: controller.setFilter),
          const SizedBox(height: 10),
          if (_notice(state, controller.reload) case final notice?)
            Padding(padding: const EdgeInsets.fromLTRB(20, 0, 20, 10), child: notice),
          Expanded(
            child: Stack(
              children: [
                // El lector de pantalla anuncia la superficie del mapa, que se toca y se arrastra
                // (fase 8, fila 145); cada marcador lleva su propia etiqueta.
                Semantics(
                  label: 'Mapa de reportes. Toca un marcador para ver su ficha',
                  child: FlutterMap(
                    mapController: _map,
                    options: MapOptions(
                      initialCenter: _pastoCenter,
                      initialZoom: _initialZoom,
                      minZoom: _minZoom,
                      maxZoom: _maxZoom,
                      backgroundColor: AppTokens.mapGround,
                      // Sin rotación: el área visible es siempre un rectángulo norte-sur.
                      interactionOptions: const InteractionOptions(
                        flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
                      ),
                      onMapReady: _onReady,
                      onPositionChanged: (_, _) => _onMoved(),
                      onTap: (_, _) => controller.select(null),
                    ),
                    children: [
                      ref.watch(mapTileLayerProvider),
                      MarkerLayer(
                        markers: [
                          for (final report in state.reports)
                            Marker(
                              point: LatLng(report.latitude, report.longitude),
                              width: AppTokens.minTouchTarget,
                              height: AppTokens.minTouchTarget,
                              child: _Pin(
                                report: report,
                                selected: report.id == state.selectedId,
                                onTap: () => controller.select(report.id),
                              ),
                            ),
                        ],
                      ),
                      const _Attribution(),
                    ],
                  ),
                ),
                if (state.loading)
                  const Positioned(
                    top: 0,
                    left: 0,
                    right: 0,
                    child: LinearProgressIndicator(
                      minHeight: 3,
                      color: AppTokens.ink,
                      backgroundColor: AppTokens.line,
                      semanticsLabel: 'Cargando reportes',
                    ),
                  ),
              ],
            ),
          ),
          if (selected != null)
            _ReportCard(
              report: selected,
              confirming: state.confirming,
              error: state.confirmError,
              onConfirm: () => controller.confirm(selected),
              onOpen: () => context.push(AppRoutes.reportDetailOf(selected.id)),
              onClose: () => controller.select(null),
            ),
        ],
      ),
    );
  }

  /// Aviso sobre el mapa: sin conexión, error con reintento, área con demasiados reportes
  /// o área sin reportes. Null si no hay nada que avisar.
  static Widget? _notice(ReportMapState state, VoidCallback onRetry) {
    final failure = state.failure;
    if (failure is NetworkFailure) {
      return _MapNotice(
        title: 'Sin conexión',
        message: state.loaded
            ? 'Mostramos los últimos reportes cargados. Para enviar un reporte necesitas internet.'
            : 'No pudimos cargar los reportes. Revisa tu señal e intenta de nuevo.',
        onRetry: onRetry,
      );
    }
    if (failure != null) {
      return _MapNotice(
        title: 'No pudimos cargar los reportes',
        message: failure.message,
        onRetry: onRetry,
      );
    }
    if (state.truncated) {
      return const _MapNotice(
        title: 'Hay más reportes en esta zona',
        message: 'Acerca el mapa para verlos todos.',
      );
    }
    if (state.loaded && !state.loading && state.reports.isEmpty) {
      return _MapNotice(
        title: 'No hay reportes en esta zona',
        message: state.filter == null
            ? 'Mueve el mapa para ver otras zonas.'
            : 'Prueba con otro estado o mueve el mapa.',
      );
    }
    return null;
  }
}

/// Atribución obligatoria de OpenStreetMap (guía 3.1), con enlace a su página de derechos.
/// Es un widget propio porque el de `flutter_map` se desborda con el texto del sistema grande.
class _Attribution extends ConsumerWidget {
  const _Attribution();

  static final Uri _copyright = Uri.parse('https://www.openstreetmap.org/copyright');

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Align(
      alignment: Alignment.bottomRight,
      child: Semantics(
        container: true,
        link: true,
        child: Material(
          color: AppTokens.surface.withValues(alpha: 0.85),
          child: InkWell(
            onTap: () => ref.read(urlOpenerProvider)(_copyright),
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 6, vertical: 3),
              child: Text(
                '© Colaboradores de OpenStreetMap',
                style: TextStyle(fontSize: 11, color: AppTokens.cardText),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Filtros por estado (Figma `4:2`): cada uno con su punto de color y su nombre, así que
/// también sirven de leyenda del mapa.
class _Filters extends StatelessWidget {
  const _Filters({required this.selected, required this.onSelected});

  final ReportStatus? selected;
  final ValueChanged<ReportStatus?> onSelected;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: [
          _FilterPill(label: 'Todos', selected: selected == null, onTap: () => onSelected(null)),
          for (final status in ReportStatus.values) ...[
            const SizedBox(width: 8),
            _FilterPill(
              label: status.label,
              dot: _statusColor(status),
              selected: selected == status,
              onTap: () => onSelected(status),
            ),
          ],
        ],
      ),
    );
  }
}

class _FilterPill extends StatelessWidget {
  const _FilterPill({required this.label, required this.selected, required this.onTap, this.dot});

  final String label;
  final Color? dot;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: 'Filtro $label',
      excludeSemantics: true,
      child: Material(
        color: selected ? AppTokens.ink : AppTokens.surface,
        shape: StadiumBorder(side: BorderSide(color: selected ? AppTokens.ink : AppTokens.line)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: AppTokens.minTouchTarget),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (dot != null) ...[
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(color: dot, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 8),
                  ],
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: selected ? AppTokens.surface : AppTokens.ink,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Marcador de un reporte: punto del color de su estado en un área táctil de 44 px. El
/// estado también se lee en la etiqueta y en la ficha, no solo en el color (guía 10.3).
class _Pin extends StatelessWidget {
  const _Pin({required this.report, required this.selected, required this.onTap});

  final MapReport report;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = _statusColor(report.status);
    final size = selected ? 30.0 : 22.0;
    return Semantics(
      // Nodo propio: sin esto el lector de pantalla lo une con la atribución del mapa.
      container: true,
      button: true,
      selected: selected,
      label: 'Reporte ${report.status.label} en ${report.address}',
      excludeSemantics: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: Center(
          child: Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              border: Border.all(color: AppTokens.surface, width: selected ? 4 : 3),
              boxShadow: [BoxShadow(color: AppTokens.ink.withValues(alpha: 0.25), blurRadius: 4)],
            ),
          ),
        ),
      ),
    );
  }
}

/// Aviso en línea sobre el mapa (Figma `16:359`, «Sin conexión»), con reintento opcional.
class _MapNotice extends StatelessWidget {
  const _MapNotice({required this.title, required this.message, this.onRetry});

  final String title;
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      container: true,
      child: Container(
        padding: const EdgeInsets.fromLTRB(14, 10, 6, 10),
        decoration: BoxDecoration(
          color: AppTokens.amberSoft,
          border: Border.all(color: AppTokens.prioritizedFg),
          borderRadius: BorderRadius.circular(AppTokens.buttonRadius),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(message, style: const TextStyle(fontSize: 13, height: 19 / 13)),
                ],
              ),
            ),
            if (onRetry != null)
              TextButton(
                onPressed: onRetry,
                style: TextButton.styleFrom(
                  foregroundColor: AppTokens.ink,
                  minimumSize: const Size(AppTokens.minTouchTarget, AppTokens.minTouchTarget),
                ),
                child: const Text('Reintentar', style: TextStyle(fontWeight: FontWeight.w700)),
              )
            else
              const SizedBox(width: 8),
          ],
        ),
      ),
    );
  }
}

/// Ficha del reporte elegido. Un reporte ajeno muestra solo la vista pública y ofrece
/// «Confirmar este daño»; el propio o el ya confirmado enlazan a su detalle.
class _ReportCard extends StatelessWidget {
  const _ReportCard({
    required this.report,
    required this.confirming,
    required this.error,
    required this.onConfirm,
    required this.onOpen,
    required this.onClose,
  });

  final MapReport report;
  final bool confirming;
  final String? error;
  final VoidCallback onConfirm;
  final VoidCallback onOpen;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    final confirmations = switch (report.confirmations) {
      0 => 'Nadie ha confirmado este daño aún',
      1 => '1 vecino confirmó este daño',
      final n => '$n vecinos confirmaron este daño',
    };
    final relation = report.isMine
        ? 'Tu reporte'
        : report.confirmedByMe
        ? 'Lo confirmaste'
        : null;
    return Container(
      decoration: const BoxDecoration(
        color: AppTokens.surface,
        border: Border(top: BorderSide(color: AppTokens.line)),
      ),
      // La ficha no ocupa más de la mitad de la pantalla: con el texto grande, se desplaza.
      constraints: BoxConstraints(maxHeight: MediaQuery.sizeOf(context).height * 0.5),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 6, 8, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      StatusChip(report.status),
                      SeverityChip(report.severity),
                      Text(
                        formatRelative(report.createdAt, DateTime.now().toUtc()),
                        style: const TextStyle(fontSize: 13, color: AppTokens.textSecondary),
                      ),
                    ],
                  ),
                ),
                Semantics(
                  button: true,
                  label: 'Cerrar ficha',
                  excludeSemantics: true,
                  child: InkResponse(
                    onTap: onClose,
                    radius: AppTokens.minTouchTarget / 2,
                    child: SizedBox.square(
                      dimension: AppTokens.minTouchTarget,
                      child: Center(child: SvgPicture.asset('assets/icons/close.svg')),
                    ),
                  ),
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    report.address,
                    style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    relation == null ? confirmations : '$relation · $confirmations',
                    style: const TextStyle(fontSize: 13, color: AppTokens.textSecondary),
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 8),
                    Semantics(
                      liveRegion: true,
                      child: Text(
                        error!,
                        style: const TextStyle(fontSize: 13, color: AppTokens.errorAccent),
                      ),
                    ),
                  ],
                  if (report.canConfirm) ...[
                    const SizedBox(height: 12),
                    PrimaryButton(
                      label: 'Confirmar este daño',
                      loading: confirming,
                      onPressed: onConfirm,
                    ),
                    const SizedBox(height: 6),
                    // Propuesta 112: el servidor rechaza a quien está lejos del daño.
                    const Text(
                      'Solo puedes confirmarlo si estás a menos de 50 m del daño.',
                      style: TextStyle(fontSize: 12, color: AppTokens.textSecondary),
                    ),
                  ],
                  if (report.canOpenDetail) ...[
                    const SizedBox(height: 12),
                    PrimaryButton(
                      label: 'Ver detalle',
                      variant: ButtonVariant.outline,
                      onPressed: onOpen,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
