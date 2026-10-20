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
import '../application/report_draft_controller.dart';
import '../application/submit_report_controller.dart';
import '../domain/submit_outcome.dart';

/// Esqueleto común de las pantallas de error del envío: volver, contenido y dos botones.
class _ErrorScaffold extends StatelessWidget {
  const _ErrorScaffold({
    required this.children,
    required this.primaryLabel,
    required this.onPrimary,
    required this.secondaryLabel,
    required this.onSecondary,
  });

  final List<Widget> children;
  final String primaryLabel;
  final VoidCallback onPrimary;
  final String secondaryLabel;
  final VoidCallback onSecondary;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: FillScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
          children: [
            AppBackButton(
              onPressed: () => context.canPop() ? context.pop() : context.go(AppRoutes.myReports),
            ),
            ...children,
            const SizedBox(height: 24),
            PrimaryButton(label: primaryLabel, variant: ButtonVariant.dark, onPressed: onPrimary),
            const SizedBox(height: 10),
            PrimaryButton(
              label: secondaryLabel,
              variant: ButtonVariant.secondary,
              onPressed: onSecondary,
            ),
          ],
        ),
      ),
    );
  }
}

TextStyle? _title(BuildContext context, double size, double lineHeight) =>
    Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: size, height: lineHeight / size);

const _body = TextStyle(fontSize: 15, height: 22 / 15, color: AppTokens.textSecondary);

/// Abandona el reporte: el borrador se descarta.
void _cancelReport(BuildContext context, WidgetRef ref) {
  ref.read(reportDraftProvider.notifier).reset();
  context.go(AppRoutes.myReports);
}

/// Fuera del área de servicio (Figma `15:2`, error 422 `LOCATION_OUTSIDE_SERVICE_AREA`).
///
/// La app no permite elegir el punto en un mapa (fuera del alcance), así que en lugar de
/// «Mover el punto» ofrece volver a tomar la ubicación desde el lugar del daño.
class OutsideAreaScreen extends ConsumerWidget {
  const OutsideAreaScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _ErrorScaffold(
      primaryLabel: 'Volver a tomar la ubicación',
      onPrimary: () {
        ref.read(reportDraftProvider.notifier).discardLocation();
        context.go(AppRoutes.newReport);
      },
      secondaryLabel: 'Cancelar reporte',
      onSecondary: () => _cancelReport(context, ref),
      children: [
        const SizedBox(height: 16),
        const _ServiceAreaIllustration(),
        const SizedBox(height: 22),
        Semantics(
          header: true,
          child: Text('Este punto está fuera del área de servicio', style: _title(context, 28, 34)),
        ),
        const SizedBox(height: 8),
        const Text(
          'Street Repo atiende reportes dentro del casco urbano de Pasto. Si el daño está '
          'dentro, toma la ubicación de nuevo desde el lugar del daño.',
          style: _body,
        ),
        const Spacer(),
      ],
    );
  }
}

/// Ilustración del Figma: el área de servicio punteada y el punto rojo por fuera.
class _ServiceAreaIllustration extends StatelessWidget {
  const _ServiceAreaIllustration();

  @override
  Widget build(BuildContext context) {
    Widget street({double? left, double? top, double? width, double? height}) => Positioned(
      left: left,
      top: top,
      width: width,
      height: height,
      child: const Opacity(opacity: 0.9, child: ColoredBox(color: AppTokens.surface)),
    );
    return ExcludeSemantics(
      child: Container(
        height: 200,
        width: double.infinity,
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          color: AppTokens.mapGround,
          borderRadius: BorderRadius.circular(AppTokens.cardRadius),
        ),
        child: Stack(
          children: [
            Positioned(
              left: 20,
              top: 35,
              width: 190,
              height: 130,
              child: CustomPaint(painter: _DashedAreaPainter()),
            ),
            street(left: 60, top: 0, width: 3, height: 200),
            street(left: 5, top: 85, width: 330, height: 3),
            street(left: 140, top: 0, width: 3, height: 200),
            street(left: 5, top: 145, width: 330, height: 3),
            Positioned(
              left: 270,
              top: 90,
              child: SvgPicture.asset('assets/icons/point_outside.svg'),
            ),
          ],
        ),
      ),
    );
  }
}

class _DashedAreaPainter extends CustomPainter {
  static const double _dash = 6;
  static const double _gap = 4;

  @override
  void paint(Canvas canvas, Size size) {
    final area = RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(12));
    canvas.drawRRect(area, Paint()..color = AppTokens.link.withValues(alpha: 0.12));
    final stroke = Paint()
      ..color = AppTokens.link
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    final border = Path()..addRRect(area.deflate(1));
    for (final metric in border.computeMetrics()) {
      for (var start = 0.0; start < metric.length; start += _dash + _gap) {
        canvas.drawPath(metric.extractPath(start, start + _dash), stroke);
      }
    }
  }

  @override
  bool shouldRepaint(_DashedAreaPainter oldDelegate) => false;
}

/// Límite alcanzado (Figma `15:25`, 429 de reportes o de consultas cercanas). El borrador se
/// conserva: «Entendido» vuelve al paso 2.
class RateLimitedScreen extends ConsumerStatefulWidget {
  const RateLimitedScreen({super.key});

  @override
  ConsumerState<RateLimitedScreen> createState() => _RateLimitedScreenState();
}

class _RateLimitedScreenState extends ConsumerState<RateLimitedScreen> {
  late final Duration _wait;

  @override
  void initState() {
    super.initState();
    final outcome = ref.read(submitReportProvider).outcome;
    _wait = outcome is RateLimited ? outcome.retryAfter : Duration.zero;
  }

  @override
  Widget build(BuildContext context) {
    return _ErrorScaffold(
      primaryLabel: 'Entendido',
      onPrimary: () => context.canPop() ? context.pop() : context.go(AppRoutes.myReports),
      secondaryLabel: 'Ver mis reportes',
      onSecondary: () => context.go(AppRoutes.myReports),
      children: [
        const Spacer(),
        Center(
          child: ExcludeSemantics(
            child: Container(
              width: 88,
              height: 88,
              alignment: Alignment.center,
              decoration: const BoxDecoration(color: AppTokens.amberSoft, shape: BoxShape.circle),
              child: Text(
                '!',
                style: _title(context, 40, 48)?.copyWith(color: AppTokens.prioritizedFg),
              ),
            ),
          ),
        ),
        const SizedBox(height: 14),
        SizedBox(
          width: double.infinity,
          child: Semantics(
            header: true,
            child: Text(
              'Alcanzaste el límite de reportes',
              textAlign: TextAlign.center,
              style: _title(context, 26, 32),
            ),
          ),
        ),
        const SizedBox(height: 14),
        const SizedBox(
          width: double.infinity,
          child: Text(
            'Para evitar abusos, hay un máximo de reportes por hora. Tus reportes anteriores ya '
            'están registrados.',
            textAlign: TextAlign.center,
            style: _body,
          ),
        ),
        const SizedBox(height: 18),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          decoration: BoxDecoration(
            color: AppTokens.amberSoft,
            borderRadius: BorderRadius.circular(AppTokens.cardRadius),
          ),
          child: Semantics(
            label: 'Podrás enviar otro en ${formatWait(_wait)}',
            excludeSemantics: true,
            child: Column(
              children: [
                const Text(
                  'Podrás enviar otro en',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 13, color: AppTokens.textSecondary),
                ),
                Text(
                  formatWait(_wait),
                  textAlign: TextAlign.center,
                  style: _title(context, 34, 41),
                ),
              ],
            ),
          ),
        ),
        const Spacer(),
      ],
    );
  }
}

/// Foto rechazada (Figma `15:46`: 413, 415 o 422 de la foto). El mensaje es el del servidor.
class PhotoRejectedScreen extends ConsumerStatefulWidget {
  const PhotoRejectedScreen({super.key});

  @override
  ConsumerState<PhotoRejectedScreen> createState() => _PhotoRejectedScreenState();
}

class _PhotoRejectedScreenState extends ConsumerState<PhotoRejectedScreen> {
  late final String _message;

  @override
  void initState() {
    super.initState();
    final outcome = ref.read(submitReportProvider).outcome;
    _message = outcome is PhotoRejected
        ? outcome.message
        : 'Usa una imagen JPEG, PNG o WebP de hasta 10 MB.';
  }

  @override
  Widget build(BuildContext context) {
    return _ErrorScaffold(
      primaryLabel: 'Tomar otra foto',
      onPrimary: () {
        ref.read(reportDraftProvider.notifier).discardPhoto();
        context.go(AppRoutes.newReport);
      },
      secondaryLabel: 'Cancelar reporte',
      onSecondary: () => _cancelReport(context, ref),
      children: [
        const SizedBox(height: 12),
        Semantics(header: true, child: Text('Foto del daño', style: _title(context, 28, 34))),
        const SizedBox(height: 8),
        const Text('Paso 1 de 2', style: _body),
        const SizedBox(height: 16),
        ExcludeSemantics(
          child: Container(
            height: 260,
            width: double.infinity,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppTokens.sand,
              border: Border.all(color: AppTokens.errorAccent, width: 2),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Container(
              width: 56,
              height: 56,
              alignment: Alignment.center,
              decoration: const BoxDecoration(
                color: AppTokens.errorSurface,
                shape: BoxShape.circle,
              ),
              child: Text(
                '!',
                style: _title(context, 25, 30)?.copyWith(color: AppTokens.errorAccent),
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        NoticeBanner(title: 'No pudimos usar esta foto', message: _message),
        const Spacer(),
      ],
    );
  }
}
