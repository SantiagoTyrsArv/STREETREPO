import 'package:flutter/material.dart';

import '../theme/app_tokens.dart';

/// Campo del Figma: etiqueta de 13 px seminegrita arriba, campo blanco de 52 px y, si hace
/// falta, ayuda o error debajo. Lo escrito vive en [controller] y se conserva ante errores.
class LabeledField extends StatelessWidget {
  const LabeledField({
    required this.label,
    required this.controller,
    this.errorText,
    this.helperText,
    this.obscureText = false,
    this.keyboardType,
    this.textInputAction,
    this.autofillHints,
    this.onSubmitted,
    this.enabled = true,
    super.key,
  });

  final String label;
  final TextEditingController controller;
  final String? errorText;
  final String? helperText;
  final bool obscureText;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final Iterable<String>? autofillHints;
  final ValueChanged<String>? onSubmitted;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ExcludeSemantics(
          child: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        ),
        const SizedBox(height: 6),
        // La etiqueta visible está arriba; el lector de pantalla la oye en el campo.
        Semantics(
          label: label,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: AppTokens.fieldHeight),
            child: TextField(
              controller: controller,
              enabled: enabled,
              obscureText: obscureText,
              autocorrect: !obscureText,
              enableSuggestions: !obscureText,
              keyboardType: keyboardType,
              textInputAction: textInputAction,
              autofillHints: autofillHints,
              onSubmitted: onSubmitted,
              style: const TextStyle(fontSize: 16, color: AppTokens.ink),
              // El error solo pinta el borde; el texto va debajo, alineado con el campo como en el Figma.
              decoration: InputDecoration(
                error: errorText == null ? null : const SizedBox.shrink(),
              ),
            ),
          ),
        ),
        if (errorText ?? helperText case final note?) ...[
          const SizedBox(height: 6),
          Semantics(
            liveRegion: errorText != null,
            child: Text(
              note,
              style: TextStyle(
                fontSize: 12,
                color: errorText != null ? AppTokens.errorAccent : AppTokens.textSecondary,
              ),
            ),
          ),
        ],
      ],
    );
  }
}
