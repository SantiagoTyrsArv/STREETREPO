import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../theme/app_tokens.dart';

/// «Volver» del Figma: icono de 24 px en un área táctil de 44 px.
class AppBackButton extends StatelessWidget {
  const AppBackButton({required this.onPressed, super.key});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Volver',
      excludeSemantics: true,
      child: InkResponse(
        onTap: onPressed,
        radius: AppTokens.minTouchTarget / 2,
        child: SizedBox.square(
          dimension: AppTokens.minTouchTarget,
          child: Center(child: SvgPicture.asset('assets/icons/back.svg')),
        ),
      ),
    );
  }
}
