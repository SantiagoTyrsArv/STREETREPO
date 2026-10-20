import 'package:flutter/material.dart';

import '../theme/app_tokens.dart';

enum ButtonVariant {
  /// Ámbar sobre tinta: la acción principal de la pantalla.
  primary,

  /// Borde sobre fondo oscuro («Ya tengo cuenta» de la Bienvenida).
  outlineOnDark,

  /// Borde sobre papel: acciones secundarias.
  outline,

  /// Tinta con texto blanco: «Entrar», «Crear cuenta», «Aceptar y continuar».
  dark,
}

/// Botón del Figma: 54 px de alto y radio 14. Mientras [loading] está activo no responde,
/// para evitar el doble envío (guía 10.3).
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    required this.label,
    required this.onPressed,
    this.loading = false,
    this.variant = ButtonVariant.primary,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final ButtonVariant variant;

  @override
  Widget build(BuildContext context) {
    final (background, foreground, border) = switch (variant) {
      ButtonVariant.primary => (AppTokens.amber, AppTokens.ink, null),
      ButtonVariant.outlineOnDark => (AppTokens.ink, AppTokens.onDark, AppTokens.darkBorder),
      ButtonVariant.outline => (AppTokens.surface, AppTokens.ink, AppTokens.line),
      ButtonVariant.dark => (AppTokens.ink, AppTokens.surface, null),
    };
    // El botón oscuro deshabilitado es arena con texto gris («Reintentar en 4:32» del Figma).
    final (disabledBackground, disabledForeground) = loading
        ? (background, foreground)
        : variant == ButtonVariant.dark
        ? (AppTokens.sand, AppTokens.textSecondary)
        : (background.withValues(alpha: 0.45), foreground.withValues(alpha: 0.6));
    final enabled = onPressed != null && !loading;
    return SizedBox(
      width: double.infinity,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: AppTokens.buttonHeight),
        child: FilledButton(
          onPressed: enabled ? onPressed : null,
          style: FilledButton.styleFrom(
            backgroundColor: background,
            foregroundColor: foreground,
            disabledBackgroundColor: disabledBackground,
            disabledForegroundColor: disabledForeground,
            minimumSize: const Size.fromHeight(AppTokens.buttonHeight),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppTokens.buttonRadius),
              side: border == null ? BorderSide.none : BorderSide(color: border, width: 1.5),
            ),
            textStyle: Theme.of(context).textTheme.labelLarge,
          ),
          child: loading
              ? SizedBox.square(
                  dimension: 22,
                  child: CircularProgressIndicator(strokeWidth: 2.5, color: foreground),
                )
              : Text(label, textAlign: TextAlign.center),
        ),
      ),
    );
  }
}
