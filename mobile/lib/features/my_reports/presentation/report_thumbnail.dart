import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../../core/theme/app_tokens.dart';
import '../application/my_reports_controller.dart';

/// Miniatura de la tarjeta (Figma `6:74`). Solo los reportes propios tienen foto: los bytes
/// se piden con el cliente con sesión y quedan en memoria, sin caché en disco
/// (propuesta 54). Mientras carga, si falla o si no hay foto, se ve el ícono de cámara.
class ReportThumbnail extends ConsumerWidget {
  const ReportThumbnail({required this.reportId, required this.hasPhoto, super.key});

  static const double size = 60;

  final String reportId;
  final bool hasPhoto;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bytes = hasPhoto ? ref.watch(reportThumbnailProvider(reportId)).value : null;
    final pixels = (size * MediaQuery.devicePixelRatioOf(context)).round();
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppTokens.fieldRadius),
      child: SizedBox.square(
        dimension: size,
        child: bytes == null
            ? ColoredBox(
                color: AppTokens.thumbnail,
                child: Center(
                  child: ExcludeSemantics(child: SvgPicture.asset('assets/icons/cam.svg')),
                ),
              )
            : Image.memory(
                bytes,
                fit: BoxFit.cover,
                cacheWidth: pixels,
                gaplessPlayback: true,
                semanticLabel: 'Foto del daño',
              ),
      ),
    );
  }
}
