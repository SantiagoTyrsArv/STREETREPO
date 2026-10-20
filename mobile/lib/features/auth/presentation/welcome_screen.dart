import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/primary_button.dart';

/// Bienvenida (Figma `2:3`).
class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  // Posición de la línea de calzada en el marco de 390×844 del Figma.
  static const double _roadLineTop = 455;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      backgroundColor: AppTokens.ink,
      body: Stack(
        children: [
          Positioned(
            left: 0,
            top: _roadLineTop,
            child: ExcludeSemantics(child: SvgPicture.asset('assets/icons/welcome_road_line.svg')),
          ),
          SafeArea(
            child: FillScrollView(
              padding: const EdgeInsets.fromLTRB(28, 56, 28, 32),
              children: [
                const _Logo(),
                const SizedBox(height: 92),
                Semantics(
                  header: true,
                  child: Text.rich(
                    const TextSpan(
                      children: [
                        TextSpan(text: 'Reporta los daños de tu vía.\n'),
                        TextSpan(
                          text: 'Ayuda a decidir cuál se repara primero.',
                          style: TextStyle(color: AppTokens.amber),
                        ),
                      ],
                    ),
                    style: theme.textTheme.headlineLarge?.copyWith(
                      color: AppTokens.onDark,
                      height: 40 / 38,
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Sistema ciudadano de reporte y priorización de daños en la infraestructura '
                  'vial de Pasto, Nariño.',
                  style: TextStyle(fontSize: 16, height: 24 / 16, color: AppTokens.onDarkMuted),
                ),
                const Spacer(),
                const SizedBox(height: 24),
                const _Benefit(icon: 'welcome_cam', text: 'Toma una foto del daño'),
                const SizedBox(height: 10),
                const _Benefit(
                  icon: 'welcome_pin',
                  text: 'Se ubica con tu GPS y se asocia a la vía',
                ),
                const SizedBox(height: 10),
                const _Benefit(icon: 'welcome_check', text: 'Sigue su estado hasta que se repare'),
                const SizedBox(height: 20),
                PrimaryButton(
                  label: 'Crear cuenta',
                  onPressed: () => context.push(AppRoutes.register),
                ),
                const SizedBox(height: 12),
                PrimaryButton(
                  label: 'Ya tengo cuenta',
                  variant: ButtonVariant.outlineOnDark,
                  onPressed: () => context.push(AppRoutes.login),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Logo extends StatelessWidget {
  const _Logo();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: AppTokens.minTouchTarget,
          height: AppTokens.minTouchTarget,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppTokens.amber,
            borderRadius: BorderRadius.circular(AppTokens.fieldRadius),
          ),
          child: ExcludeSemantics(child: SvgPicture.asset('assets/icons/pin_brand.svg')),
        ),
        const SizedBox(width: 12),
        Text(
          'Street Repo',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: AppTokens.onDark),
        ),
      ],
    );
  }
}

class _Benefit extends StatelessWidget {
  const _Benefit({required this.icon, required this.text});

  final String icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        ExcludeSemantics(child: SvgPicture.asset('assets/icons/$icon.svg')),
        const SizedBox(width: 10),
        Expanded(
          child: Text(text, style: const TextStyle(fontSize: 14, color: AppTokens.onDarkSoft)),
        ),
      ],
    );
  }
}
