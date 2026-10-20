import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/app_back_button.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/primary_button.dart';
import '../application/report_draft_controller.dart';
import '../domain/device_services.dart';

/// Sin acceso a la ubicación (Figma `14:116`): permiso negado de forma permanente o GPS
/// apagado. Al volver de los ajustes con la ubicación activa, sigue al paso 1 solo.
class PermissionDeniedScreen extends ConsumerStatefulWidget {
  const PermissionDeniedScreen({super.key});

  @override
  ConsumerState<PermissionDeniedScreen> createState() => _PermissionDeniedScreenState();
}

class _PermissionDeniedScreenState extends ConsumerState<PermissionDeniedScreen> {
  late final AppLifecycleListener _lifecycle;

  @override
  void initState() {
    super.initState();
    // Al regresar de los ajustes del teléfono se vuelve a comprobar el permiso.
    _lifecycle = AppLifecycleListener(onResume: _recheck);
  }

  @override
  void dispose() {
    _lifecycle.dispose();
    super.dispose();
  }

  void _leave() => context.canPop() ? context.pop() : context.go(AppRoutes.myReports);

  Future<void> _recheck() async {
    final state = await ref.read(reportDraftProvider.notifier).locationAccess();
    if (!mounted) return;
    if (state == LocationPermissionState.granted) {
      context.pushReplacement(AppRoutes.newReport);
    } else if (state == LocationPermissionState.denied) {
      // Se reactivó la posibilidad de pedirlo: se explica de nuevo antes de pedirlo.
      context.pushReplacement(AppRoutes.newReportPermissions);
    }
  }

  Future<void> _openSettings() async {
    final controller = ref.read(reportDraftProvider.notifier);
    await controller.openLocationSettings(await controller.locationAccess());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: FillScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
          children: [
            AppBackButton(onPressed: _leave),
            const Spacer(),
            const SizedBox(height: 16),
            Center(
              child: ExcludeSemantics(
                child: Container(
                  width: 88,
                  height: 88,
                  alignment: Alignment.center,
                  decoration: const BoxDecoration(
                    color: AppTokens.amberSoft,
                    shape: BoxShape.circle,
                  ),
                  child: Text(
                    '!',
                    style: theme.textTheme.headlineLarge?.copyWith(
                      color: AppTokens.prioritizedFg,
                      fontSize: 40,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: Semantics(
                header: true,
                child: Text(
                  'Sin acceso a la ubicación',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.headlineMedium?.copyWith(fontSize: 26, height: 32 / 26),
                ),
              ),
            ),
            const SizedBox(height: 16),
            const SizedBox(
              width: double.infinity,
              child: Text(
                'No podemos fijar el punto del daño sin tu ubicación. Actívala en los ajustes del '
                'teléfono para continuar con el reporte.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 15, height: 22 / 15, color: AppTokens.textSecondary),
              ),
            ),
            const Spacer(),
            const SizedBox(height: 24),
            PrimaryButton(
              label: 'Abrir ajustes',
              variant: ButtonVariant.dark,
              onPressed: _openSettings,
            ),
            const SizedBox(height: 10),
            PrimaryButton(label: 'Volver', variant: ButtonVariant.secondary, onPressed: _leave),
          ],
        ),
      ),
    );
  }
}
