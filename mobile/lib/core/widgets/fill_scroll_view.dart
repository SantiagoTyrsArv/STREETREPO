import 'package:flutter/material.dart';

/// Columna que ocupa al menos el alto de la pantalla (para empujar los botones abajo con un
/// `Spacer`, como el «Relleno» del Figma) y se desplaza cuando el contenido no cabe, p. ej.
/// con el texto del sistema al doble de tamaño.
class FillScrollView extends StatelessWidget {
  const FillScrollView({required this.children, required this.padding, super.key});

  final List<Widget> children;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        padding: padding,
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: constraints.maxHeight - padding.vertical),
          child: IntrinsicHeight(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
          ),
        ),
      ),
    );
  }
}
