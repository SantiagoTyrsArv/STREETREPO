import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../routing/app_router.dart';
import '../theme/app_tokens.dart';

/// Barra de navegación del Figma (`6:122`): Reportar · Mis reportes · Perfil. La pestaña Mapa
/// se omite en esta entrega porque el mapa está fuera del alcance (spec 2.2).
class AppShell extends StatelessWidget {
  const AppShell({required this.location, required this.child, super.key});

  final String location;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: DecoratedBox(
        decoration: const BoxDecoration(
          color: AppTokens.surface,
          border: Border(top: BorderSide(color: AppTokens.line)),
        ),
        child: SafeArea(
          top: false,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 76),
            child: IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(
                    child: _Tab(
                      label: 'Reportar',
                      selected: false,
                      isAction: true,
                      icon: Container(
                        width: AppTokens.minTouchTarget,
                        height: AppTokens.minTouchTarget,
                        alignment: Alignment.center,
                        decoration: const BoxDecoration(
                          color: AppTokens.amber,
                          shape: BoxShape.circle,
                        ),
                        child: SvgPicture.asset('assets/icons/plus.svg'),
                      ),
                      onTap: () => context.push(AppRoutes.newReport),
                    ),
                  ),
                  Expanded(
                    child: _Tab(
                      label: 'Mis reportes',
                      selected: location == AppRoutes.myReports,
                      icon: SvgPicture.asset(
                        location == AppRoutes.myReports
                            ? 'assets/icons/list.svg'
                            : 'assets/icons/list_inactive.svg',
                      ),
                      onTap: () => context.go(AppRoutes.myReports),
                    ),
                  ),
                  Expanded(
                    child: _Tab(
                      label: 'Perfil',
                      selected: location == AppRoutes.profile,
                      icon: SvgPicture.asset(
                        location == AppRoutes.profile
                            ? 'assets/icons/user_active.svg'
                            : 'assets/icons/user.svg',
                      ),
                      onTap: () => context.go(AppRoutes.profile),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Tab extends StatelessWidget {
  const _Tab({
    required this.label,
    required this.selected,
    required this.icon,
    required this.onTap,
    this.isAction = false,
  });

  final String label;
  final bool selected;

  /// «Reportar» es una acción, no una pestaña: su texto va en tinta aunque no esté elegida.
  final bool isAction;
  final Widget icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: isAction ? null : selected,
      label: label,
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              icon,
              const SizedBox(height: 3),
              Text(
                label,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w600,
                  color: selected || isAction ? AppTokens.ink : AppTokens.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
