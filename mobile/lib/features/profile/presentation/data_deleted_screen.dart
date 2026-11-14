import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format/formatters.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/primary_button.dart';
import '../../auth/domain/session.dart';

/// Supresión atendida · Constancia (Figma `16:218`). Se muestra ya fuera de sesión: la
/// cuenta no existe. Los datos de la constancia son los que devolvió el servidor.
class DataDeletedScreen extends StatelessWidget {
  const DataDeletedScreen({required this.receipt, super.key});

  final DeletionReceipt receipt;

  @override
  Widget build(BuildContext context) {
    final titleStyle = Theme.of(context).textTheme.headlineMedium
        ?.copyWith(fontSize: 24, height: 30 / 24);
    final attended = receipt.attendedAt;
    return Scaffold(
      body: SafeArea(
        child: FillScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          children: [
            const Spacer(),
            Center(
              child: ExcludeSemantics(
                child: Container(
                  width: 88,
                  height: 88,
                  alignment: Alignment.center,
                  decoration: const BoxDecoration(
                    color: AppTokens.repairedChip,
                    shape: BoxShape.circle,
                  ),
                  child: Text(
                    '✓',
                    style: titleStyle?.copyWith(fontSize: 40, color: AppTokens.repairedFg),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: Semantics(
                header: true,
                liveRegion: true,
                child: Text(
                  'Tus datos fueron eliminados',
                  style: titleStyle,
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            const SizedBox(height: 14),
            const SizedBox(
              width: double.infinity,
              child: Text(
                'Tu solicitud fue atendida de inmediato. Tu correo queda libre para un '
                'registro nuevo.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 15, height: 22 / 15, color: AppTokens.textSecondary),
              ),
            ),
            const SizedBox(height: 20),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTokens.surface,
                border: Border.all(color: AppTokens.line),
                borderRadius: BorderRadius.circular(AppTokens.cardRadius),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Constancia de la solicitud',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
                  ),
                  _Row(label: 'Estado', value: _statusLabel(receipt.status)),
                  _Row(label: 'Solicitud', value: formatDateTime(receipt.requestedAt)),
                  if (attended != null) _Row(label: 'Atención', value: formatDateTime(attended)),
                  const _Row(label: 'Sesiones', value: 'Todas cerradas'),
                ],
              ),
            ),
            const Spacer(),
            const SizedBox(height: 24),
            PrimaryButton(
              label: 'Finalizar',
              variant: ButtonVariant.dark,
              onPressed: () => context.go(AppRoutes.welcome),
            ),
          ],
        ),
      ),
    );
  }

  /// El servidor informa el estado en minúsculas (`atendida`); se muestra con mayúscula.
  static String _statusLabel(String status) =>
      status.isEmpty ? status : status[0].toUpperCase() + status.substring(1);
}

class _Row extends StatelessWidget {
  const _Row({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: MergeSemantics(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 13, color: AppTokens.textSecondary)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                value,
                textAlign: TextAlign.end,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
