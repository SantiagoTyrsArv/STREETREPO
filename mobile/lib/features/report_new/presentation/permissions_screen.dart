import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/app_back_button.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/notice_banner.dart';
import '../../../core/widgets/primary_button.dart';
import '../application/report_draft_controller.dart';
import '../domain/device_services.dart';

/// Permisos de cámara y ubicación, pedidos en contexto y con explicación (Figma `14:80`).
///
/// El botón pide la ubicación; la cámara es la app de cámara del sistema y no necesita un
/// permiso propio, así que la tarjeta solo explica para qué se usa.
class PermissionsScreen extends ConsumerStatefulWidget {
  const PermissionsScreen({super.key});

  @override
  ConsumerState<PermissionsScreen> createState() => _PermissionsScreenState();
}

class _PermissionsScreenState extends ConsumerState<PermissionsScreen> {
  bool _requesting = false;
  bool _deniedOnce = false;

  void _leave() => context.canPop() ? context.pop() : context.go(AppRoutes.myReports);

  Future<void> _request() async {
    setState(() => _requesting = true);
    final state = await ref.read(reportDraftProvider.notifier).requestLocationAccess();
    if (!mounted) return;
    setState(() => _requesting = false);
    switch (state) {
      case LocationPermissionState.granted:
        context.pushReplacement(AppRoutes.newReport);
      case LocationPermissionState.denied:
        setState(() => _deniedOnce = true);
      case LocationPermissionState.deniedForever:
      case LocationPermissionState.serviceDisabled:
        context.pushReplacement(AppRoutes.newReportLocationDenied);
    }
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
            const SizedBox(height: 12),
            Semantics(
              header: true,
              child: Text(
                'Antes de reportar',
                style: theme.textTheme.headlineMedium?.copyWith(height: 34 / 28),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Street Repo necesita dos permisos para registrar el daño con evidencia.',
              style: TextStyle(fontSize: 15, height: 22 / 15, color: AppTokens.textSecondary),
            ),
            const SizedBox(height: 22),
            const _PermissionCard(
              icon: 'permission_camera',
              title: 'Cámara',
              body:
                  'Para tomar la foto del daño. La foto se guarda sin los datos de ubicación del '
                  'archivo.',
            ),
            const SizedBox(height: 12),
            const _PermissionCard(
              icon: 'permission_location',
              title: 'Ubicación',
              body:
                  'Para marcar dónde está el daño y avisarte si ya fue reportado a menos de 25 m.',
            ),
            if (_deniedOnce) ...[
              const SizedBox(height: 16),
              const NoticeBanner(
                message:
                    'Sin la ubicación no se puede reportar el daño. Puedes permitirla cuando '
                    'quieras.',
              ),
            ],
            const Spacer(),
            const SizedBox(height: 24),
            PrimaryButton(
              label: 'Permitir cámara y ubicación',
              variant: ButtonVariant.dark,
              loading: _requesting,
              onPressed: _request,
            ),
            const SizedBox(height: 10),
            PrimaryButton(label: 'Ahora no', variant: ButtonVariant.secondary, onPressed: _leave),
            const SizedBox(height: 10),
            const SizedBox(
              width: double.infinity,
              child: Text(
                'Puedes cambiarlo después en los ajustes del teléfono.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: AppTokens.textSecondary),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PermissionCard extends StatelessWidget {
  const _PermissionCard({required this.icon, required this.title, required this.body});

  final String icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTokens.surface,
        border: Border.all(color: AppTokens.line),
        borderRadius: BorderRadius.circular(AppTokens.cardRadius),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ExcludeSemantics(child: SvgPicture.asset('assets/icons/$icon.svg')),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: const TextStyle(
                    fontSize: 13,
                    height: 19 / 13,
                    color: AppTokens.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
