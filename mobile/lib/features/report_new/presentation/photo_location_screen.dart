import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format/formatters.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/notice_banner.dart';
import '../../../core/widgets/primary_button.dart';
import '../application/report_draft_controller.dart';
import '../domain/device_services.dart';
import '../domain/report_draft.dart';
import 'widgets/step_header.dart';

/// Nuevo reporte, paso 1 de 2: foto y ubicación (Figma `4:77`).
///
/// La dirección y la vía asociada que muestra el Figma las calcula el servidor al crear el
/// reporte; aquí se muestran las coordenadas y su precisión (se ven en «Reporte enviado»).
class PhotoLocationScreen extends ConsumerStatefulWidget {
  const PhotoLocationScreen({super.key});

  @override
  ConsumerState<PhotoLocationScreen> createState() => _PhotoLocationScreenState();
}

class _PhotoLocationScreenState extends ConsumerState<PhotoLocationScreen> {
  bool _capturing = false;
  bool _locating = false;
  bool _photoFailed = false;
  LocateOutcome? _lastLocate;

  ReportDraftController get _draft => ref.read(reportDraftProvider.notifier);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _start());
  }

  /// Sin permiso no hay paso 1: primero la explicación, o la pantalla de ajustes.
  Future<void> _start() async {
    final access = await _draft.locationAccess();
    if (!mounted) return;
    if (access != LocationPermissionState.granted) {
      _goToAccessScreen(access);
      return;
    }
    if (ref.read(reportDraftProvider).fix == null) await _locate();
  }

  void _goToAccessScreen(LocationPermissionState access) {
    context.pushReplacement(
      access == LocationPermissionState.denied
          ? AppRoutes.newReportPermissions
          : AppRoutes.newReportLocationDenied,
    );
  }

  Future<void> _locate() async {
    setState(() => _locating = true);
    final outcome = await _draft.locate();
    if (!mounted) return;
    if (outcome case LocationAccessProblem(:final state)) {
      _goToAccessScreen(state);
      return;
    }
    setState(() {
      _locating = false;
      _lastLocate = outcome;
    });
  }

  Future<void> _takePhoto() async {
    setState(() {
      _capturing = true;
      _photoFailed = false;
    });
    var taken = false;
    try {
      taken = await _draft.capturePhoto();
    } on PhotoCaptureFailed {
      if (mounted) setState(() => _photoFailed = true);
    }
    if (!mounted) return;
    setState(() => _capturing = false);
    // La ubicación es la del momento de la foto.
    if (taken) await _locate();
  }

  void _close() => context.canPop() ? context.pop() : context.go(AppRoutes.myReports);

  @override
  Widget build(BuildContext context) {
    final draft = ref.watch(reportDraftProvider);
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: FillScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            StepHeader(step: 1, onClose: _close),
            const SizedBox(height: 20),
            Semantics(
              header: true,
              child: Text(
                'Foto y ubicación del daño',
                style: theme.textTheme.headlineMedium?.copyWith(fontSize: 26, height: 28 / 26),
              ),
            ),
            const SizedBox(height: 16),
            _PhotoBox(photo: draft.photo, capturing: _capturing, onTakePhoto: _takePhoto),
            if (_photoFailed) ...[
              const SizedBox(height: 12),
              const NoticeBanner(message: 'No pudimos guardar la foto. Intenta tomarla de nuevo.'),
            ],
            const SizedBox(height: 16),
            _LocationCard(
              fix: draft.fix,
              locating: _locating,
              lastLocate: _lastLocate,
              onRetry: _locate,
            ),
            const Spacer(),
            const SizedBox(height: 24),
            PrimaryButton(
              label: 'Continuar',
              variant: ButtonVariant.dark,
              onPressed: draft.hasEvidence && !_locating && !_capturing
                  ? () => context.push(AppRoutes.newReportSeverity)
                  : null,
            ),
          ],
        ),
      ),
    );
  }
}

class _PhotoBox extends StatelessWidget {
  const _PhotoBox({required this.photo, required this.capturing, required this.onTakePhoto});

  static const double _height = 230;

  final CapturedPhoto? photo;
  final bool capturing;
  final VoidCallback onTakePhoto;

  @override
  Widget build(BuildContext context) {
    final current = photo;
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: Container(
        height: _height,
        width: double.infinity,
        color: AppTokens.photoPlaceholder,
        child: capturing
            ? const Center(
                child: CircularProgressIndicator(
                  color: AppTokens.onDark,
                  semanticsLabel: 'Abriendo la cámara',
                ),
              )
            : current == null
            ? _EmptyPhoto(onTap: onTakePhoto)
            : _TakenPhoto(photo: current, onRetake: onTakePhoto),
      ),
    );
  }
}

class _EmptyPhoto extends StatelessWidget {
  const _EmptyPhoto({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Tomar la foto del daño',
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SvgPicture.asset('assets/icons/camera_large.svg'),
            const SizedBox(height: 8),
            const Text(
              'Toca para tomar la foto del daño',
              style: TextStyle(fontSize: 13, color: AppTokens.onDarkMuted),
            ),
          ],
        ),
      ),
    );
  }
}

class _TakenPhoto extends StatelessWidget {
  const _TakenPhoto({required this.photo, required this.onRetake});

  final CapturedPhoto photo;
  final VoidCallback onRetake;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        Image.memory(
          photo.jpegBytes,
          fit: BoxFit.cover,
          gaplessPlayback: true,
          semanticLabel: 'Foto del daño',
        ),
        Positioned(
          left: 12,
          bottom: 12,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: AppTokens.ink,
              borderRadius: BorderRadius.circular(AppTokens.chipRadius),
            ),
            child: Text(
              'JPG · ${formatFileSize(photo.sizeBytes)}',
              style: const TextStyle(fontSize: 12, color: AppTokens.surface),
            ),
          ),
        ),
        // La píldora mide 36 px como en el Figma, dentro de un área táctil de 44 px.
        Positioned(
          right: 8,
          bottom: 8,
          child: Semantics(
            button: true,
            label: 'Repetir la foto',
            excludeSemantics: true,
            child: GestureDetector(
              onTap: onRetake,
              behavior: HitTestBehavior.opaque,
              child: Padding(
                padding: const EdgeInsets.all(4),
                child: Container(
                  height: 36,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: AppTokens.surface,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: const Text(
                    'Repetir',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
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

class _LocationCard extends StatelessWidget {
  const _LocationCard({
    required this.fix,
    required this.locating,
    required this.lastLocate,
    required this.onRetry,
  });

  final GeoFix? fix;
  final bool locating;
  final LocateOutcome? lastLocate;
  final VoidCallback onRetry;

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
          // Ilustración del Figma; el mapa real llega con la pantalla de mapa.
          SizedBox(
            height: 130,
            width: double.infinity,
            child: ClipRect(
              child: ExcludeSemantics(
                child: OverflowBox(
                  maxWidth: double.infinity,
                  child: SvgPicture.asset('assets/icons/location_map.svg'),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Semantics(liveRegion: true, container: true, child: _details()),
          ),
        ],
      ),
    );
  }

  Widget _details() {
    if (locating) {
      return const Row(
        children: [
          SizedBox.square(
            dimension: 18,
            child: CircularProgressIndicator(strokeWidth: 2, color: AppTokens.ink),
          ),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'Buscando tu ubicación…',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      );
    }
    final current = fix;
    if (current != null) return _Located(fix: current);
    return switch (lastLocate) {
      LocationTooImprecise(:final accuracyMeters) => _Problem(
        message:
            'La ubicación aún no es precisa (±${accuracyMeters.round()} m). Espera unos '
            'segundos o sal a un lugar abierto.',
        onRetry: onRetry,
      ),
      LocationNotFound() => _Problem(
        message:
            'No pudimos obtener tu ubicación. Revisa que el GPS esté activo e intenta de '
            'nuevo.',
        onRetry: onRetry,
      ),
      _ => const Text(
        'La ubicación se toma con la foto.',
        style: TextStyle(fontSize: 13, color: AppTokens.textSecondary),
      ),
    };
  }
}

class _Located extends StatelessWidget {
  const _Located({required this.fix});

  final GeoFix fix;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ExcludeSemantics(child: SvgPicture.asset('assets/icons/pin_location.svg')),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    formatCoordinates(fix.latitude, fix.longitude),
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Precisión GPS ±${fix.accuracyMeters.round()} m',
                    style: const TextStyle(fontSize: 13, color: AppTokens.textSecondary),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Row(
            children: [
              ExcludeSemantics(child: SvgPicture.asset('assets/icons/check_location.svg')),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  'La vía se asocia automáticamente al enviar.',
                  style: TextStyle(fontSize: 13, color: AppTokens.cardText),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Problem extends StatelessWidget {
  const _Problem({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(message, style: const TextStyle(fontSize: 14, height: 20 / 14)),
        const SizedBox(height: 12),
        PrimaryButton(label: 'Reintentar', variant: ButtonVariant.secondary, onPressed: onRetry),
      ],
    );
  }
}
