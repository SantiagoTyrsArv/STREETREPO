import 'package:flutter/material.dart';

import '../theme/app_tokens.dart';

enum NoticeTone {
  /// Aviso rojo del Figma («Demasiados intentos fallidos»).
  error,

  /// Informativo sobre blanco (p. ej. «Tu cuenta quedó creada»); no tiene diseño propio y
  /// sigue la forma del aviso de error.
  info,
}

/// Aviso en línea con icono, título opcional y mensaje. Se anuncia al lector de pantalla.
class NoticeBanner extends StatelessWidget {
  const NoticeBanner({required this.message, this.title, this.tone = NoticeTone.error, super.key});

  final String? title;
  final String message;
  final NoticeTone tone;

  @override
  Widget build(BuildContext context) {
    final (surface, accent, glyph) = switch (tone) {
      NoticeTone.error => (AppTokens.errorSurface, AppTokens.errorAccent, '!'),
      NoticeTone.info => (AppTokens.surface, AppTokens.link, 'i'),
    };
    return Semantics(
      liveRegion: true,
      container: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: surface,
          border: Border.all(color: accent),
          borderRadius: BorderRadius.circular(AppTokens.buttonRadius),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ExcludeSemantics(
              child: Container(
                width: 24,
                height: 24,
                alignment: Alignment.center,
                decoration: BoxDecoration(color: accent, shape: BoxShape.circle),
                child: Text(
                  glyph,
                  style: const TextStyle(
                    color: AppTokens.surface,
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (title != null) ...[
                    Text(title!, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
                    const SizedBox(height: 2),
                  ],
                  Text(message, style: const TextStyle(fontSize: 13, height: 19 / 13)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
