import 'package:flutter/material.dart';

import '../theme/app_tokens.dart';
import 'primary_button.dart';

/// Estados completos de cada pantalla (guía 10.3): cargando, vacío y error con reintento.
class LoadingView extends StatelessWidget {
  const LoadingView({this.label = 'Cargando…', super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Semantics(
        label: label,
        child: const CircularProgressIndicator(color: AppTokens.ink),
      ),
    );
  }
}

/// Vacío del Figma (`16:295`): círculo ámbar con un signo, título, mensaje y acción.
class EmptyView extends StatelessWidget {
  const EmptyView({required this.title, this.message, this.action, this.glyph, super.key});

  final String title;
  final String? message;
  final Widget? action;

  /// Signo del círculo («+»); sin él no se dibuja el círculo.
  final String? glyph;

  @override
  Widget build(BuildContext context) {
    return _StateMessage(
      glyph: glyph,
      glyphSurface: AppTokens.amberSoft,
      glyphColor: AppTokens.prioritizedFg,
      title: title,
      message: message,
      action: action,
    );
  }
}

/// Error del Figma (`16:327`): círculo rojo con «!», título, mensaje y «Reintentar».
class ErrorView extends StatelessWidget {
  const ErrorView({required this.message, required this.onRetry, this.title, super.key});

  final String? title;
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return _StateMessage(
      glyph: '!',
      glyphSurface: AppTokens.errorSurface,
      glyphColor: AppTokens.errorAccent,
      title: title,
      message: message,
      action: PrimaryButton(label: 'Reintentar', onPressed: onRetry, variant: ButtonVariant.dark),
    );
  }
}

class _StateMessage extends StatelessWidget {
  const _StateMessage({
    required this.glyph,
    required this.glyphSurface,
    required this.glyphColor,
    required this.title,
    required this.message,
    required this.action,
  });

  final String? glyph;
  final Color glyphSurface;
  final Color glyphColor;
  final String? title;
  final String? message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final titleStyle = Theme.of(context).textTheme.headlineMedium
        ?.copyWith(fontSize: 24, height: 30 / 24);
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (glyph != null) ...[
              ExcludeSemantics(
                child: Container(
                  width: 88,
                  height: 88,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(color: glyphSurface, shape: BoxShape.circle),
                  child: Text(
                    glyph!,
                    style: titleStyle?.copyWith(fontSize: 40, height: 48 / 40, color: glyphColor),
                  ),
                ),
              ),
              const SizedBox(height: 14),
            ],
            if (title != null) ...[
              Semantics(
                header: true,
                child: Text(title!, style: titleStyle, textAlign: TextAlign.center),
              ),
              const SizedBox(height: 14),
            ],
            if (message != null)
              Semantics(
                liveRegion: true,
                child: Text(
                  message!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 15,
                    height: 22 / 15,
                    color: AppTokens.textSecondary,
                  ),
                ),
              ),
            if (action != null) ...[const SizedBox(height: 20), action!],
          ],
        ),
      ),
    );
  }
}
