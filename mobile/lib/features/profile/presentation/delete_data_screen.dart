import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/app_back_button.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../core/widgets/notice_banner.dart';
import '../../../core/widgets/primary_button.dart';
import '../../auth/application/session_controller.dart';
import '../application/delete_data_controller.dart';

/// Perfil · Eliminar mis datos (Figma `16:177`): derecho de supresión (Ley 1581). Es
/// irreversible, así que explica qué se elimina y qué se conserva y pide la contraseña.
class DeleteDataScreen extends ConsumerStatefulWidget {
  const DeleteDataScreen({super.key});

  @override
  ConsumerState<DeleteDataScreen> createState() => _DeleteDataScreenState();
}

class _DeleteDataScreenState extends ConsumerState<DeleteDataScreen> {
  final _password = TextEditingController();

  @override
  void dispose() {
    _password.dispose();
    super.dispose();
  }

  void _submit() {
    FocusScope.of(context).unfocus();
    ref.read(deleteDataControllerProvider.notifier).submit(_password.text);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(deleteDataControllerProvider);
    ref.listen(deleteDataControllerProvider, (previous, next) {
      final receipt = next.receipt;
      if (receipt == null || previous?.receipt != null) return;
      // Primero la constancia y después el fin de la sesión: al revés, la redirección por
      // sesión llevaría un instante a la Bienvenida.
      final session = ref.read(sessionControllerProvider.notifier);
      context.go(AppRoutes.dataDeleted, extra: receipt);
      session.accountDeleted();
    });
    // Con la supresión hecha ya no se puede volver ni reenviar.
    final busy = state.submitting || state.receipt != null;
    return PopScope(
      canPop: !busy,
      child: Scaffold(
        body: SafeArea(
          child: FillScrollView(
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
            children: [
              AppBackButton(
                onPressed: () {
                  if (!busy) context.pop();
                },
              ),
              const SizedBox(height: 8),
              Semantics(
                header: true,
                child: Text(
                  'Eliminar mis datos',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 28),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Es tu derecho de supresión (Ley 1581 de 2012). Se atiende de inmediato y no '
                'se puede deshacer.',
                style: TextStyle(fontSize: 15, height: 22 / 15, color: AppTokens.textSecondary),
              ),
              const SizedBox(height: 16),
              const _Summary(
                title: 'Qué se elimina',
                bullet: AppTokens.errorAccent,
                items: [
                  'Tu nombre y tu correo (se anonimizan).',
                  'Las fotos y descripciones de tus reportes.',
                  'Tu acceso: se cierran todas tus sesiones.',
                ],
              ),
              const SizedBox(height: 10),
              const _Summary(
                title: 'Qué se conserva',
                bullet: AppTokens.repairedFg,
                items: [
                  'Los reportes (ubicación, severidad y estado), sin tus datos personales.',
                  'La constancia de tu autorización y de esta solicitud.',
                ],
              ),
              const SizedBox(height: 14),
              if (state.error != null) ...[
                NoticeBanner(message: state.error!),
                const SizedBox(height: 14),
              ],
              LabeledField(
                label: 'Contraseña actual',
                controller: _password,
                obscureText: true,
                errorText: state.passwordError,
                enabled: !busy,
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.password],
              ),
              const Spacer(),
              const SizedBox(height: 24),
              PrimaryButton(
                label: 'Eliminar mis datos',
                variant: ButtonVariant.danger,
                loading: busy,
                onPressed: _submit,
              ),
              const SizedBox(height: 8),
              PrimaryButton(
                label: 'Cancelar',
                variant: ButtonVariant.secondary,
                onPressed: busy ? null : () => context.pop(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Tarjeta con título y viñetas («Qué se elimina», «Qué se conserva»).
class _Summary extends StatelessWidget {
  const _Summary({required this.title, required this.bullet, required this.items});

  final String title;
  final Color bullet;
  final List<String> items;

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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
          for (final item in items) ...[
            const SizedBox(height: 8),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                ExcludeSemantics(
                  child: Container(
                    width: 6,
                    height: 6,
                    margin: const EdgeInsets.only(top: 6),
                    decoration: BoxDecoration(color: bullet, shape: BoxShape.circle),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    item,
                    style: const TextStyle(
                      fontSize: 13,
                      height: 18 / 13,
                      color: AppTokens.cardText,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
