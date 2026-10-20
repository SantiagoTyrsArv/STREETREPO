import 'package:flutter/material.dart';

import '../theme/app_tokens.dart';

/// Casilla del Figma: cuadro de tinta con la marca cuando está activa y borde cuando no.
/// Toda la fila (casilla y texto) responde al toque.
class ConsentCheckbox extends StatelessWidget {
  const ConsentCheckbox({
    required this.value,
    required this.onChanged,
    required this.label,
    required this.check,
    this.size = 24,
    this.radius = 6,
    this.fontSize = 14,
    this.below,
    super.key,
  });

  final bool value;

  /// Null deshabilita la casilla (p. ej. mientras carga la política).
  final ValueChanged<bool>? onChanged;
  final String label;

  /// Marca dentro del cuadro: el Figma usa una distinta en Registro y en Política.
  final Widget check;
  final double size;
  final double radius;

  /// 13 en Registro y 14 en Política, como en el Figma.
  final double fontSize;

  /// Contenido bajo el texto que no forma parte de la casilla (el enlace «Leer la política»).
  final Widget? below;

  @override
  Widget build(BuildContext context) {
    final enabled = onChanged != null;
    final box = AnimatedContainer(
      duration: const Duration(milliseconds: 120),
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: value ? AppTokens.ink : AppTokens.surface,
        border: value ? null : Border.all(color: AppTokens.inputBorder, width: 1.5),
        borderRadius: BorderRadius.circular(radius),
      ),
      child: value ? check : null,
    );
    final row = Semantics(
      checked: value,
      enabled: enabled,
      label: label,
      excludeSemantics: true,
      child: InkWell(
        onTap: enabled ? () => onChanged!(!value) : null,
        borderRadius: BorderRadius.circular(radius),
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: AppTokens.minTouchTarget),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              box,
              const SizedBox(width: 12),
              Expanded(
                child: Opacity(
                  opacity: enabled ? 1 : 0.6,
                  child: Text(
                    label,
                    style: TextStyle(fontSize: fontSize, height: (fontSize + 6) / fontSize),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
    if (below == null) return row;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        row,
        Padding(
          padding: EdgeInsets.only(left: size + 12),
          child: below,
        ),
      ],
    );
  }
}
