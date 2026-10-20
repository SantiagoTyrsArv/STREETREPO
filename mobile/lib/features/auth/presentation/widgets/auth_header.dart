import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/routing/app_router.dart';
import '../../../../core/theme/app_tokens.dart';
import '../../../../core/widgets/app_back_button.dart';

enum AuthMode { login, register }

/// Cabecera común de «Iniciar sesión» y «Registro» (Figma `2:37` y `14:3`): volver, título,
/// subtítulo y el selector entre ambas.
class AuthHeader extends StatelessWidget {
  const AuthHeader({required this.mode, required this.title, required this.subtitle, super.key});

  final AuthMode mode;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppBackButton(
          onPressed: () => context.canPop() ? context.pop() : context.go(AppRoutes.welcome),
        ),
        const SizedBox(height: 12),
        Semantics(
          header: true,
          child: Text(title, style: theme.textTheme.headlineMedium?.copyWith(height: 34 / 28)),
        ),
        const SizedBox(height: 8),
        Text(
          subtitle,
          style: const TextStyle(fontSize: 15, height: 22 / 15, color: AppTokens.textSecondary),
        ),
        const SizedBox(height: 18),
        _ModeSelector(selected: mode),
      ],
    );
  }
}

class _ModeSelector extends StatelessWidget {
  const _ModeSelector({required this.selected});

  final AuthMode selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: AppTokens.fieldHeight),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AppTokens.sand,
        borderRadius: BorderRadius.circular(AppTokens.fieldRadius),
      ),
      child: Row(
        children: [
          _option(context, AuthMode.login, 'Iniciar sesión', AppRoutes.login),
          _option(context, AuthMode.register, 'Registrarme', AppRoutes.register),
        ],
      ),
    );
  }

  Widget _option(BuildContext context, AuthMode mode, String label, String route) {
    final active = mode == selected;
    return Expanded(
      child: Semantics(
        button: true,
        selected: active,
        child: Material(
          color: active ? AppTokens.surface : Colors.transparent,
          borderRadius: BorderRadius.circular(9),
          child: InkWell(
            borderRadius: BorderRadius.circular(9),
            // Cambiar de pestaña reemplaza la pantalla; «Volver» sigue llevando a la Bienvenida.
            onTap: active ? null : () => context.pushReplacement(route),
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: AppTokens.minTouchTarget),
              child: Center(
                child: Text(
                  label,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: active ? AppTokens.ink : AppTokens.textSecondary,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
