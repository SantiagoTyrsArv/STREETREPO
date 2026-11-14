import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../core/widgets/primary_button.dart';
import '../application/edit_profile_controller.dart';

/// Hoja «Confirma tu contraseña» (Figma `16:2` y su variante de error `16:89`). Envía el
/// cambio de datos con la contraseña; se cierra sola cuando el resultado ya no depende de
/// ella (guardado, o un error que se corrige en la pantalla de edición).
class ConfirmPasswordSheet extends ConsumerStatefulWidget {
  const ConfirmPasswordSheet({required this.name, required this.email, super.key});

  final String name;
  final String email;

  @override
  ConsumerState<ConfirmPasswordSheet> createState() => _ConfirmPasswordSheetState();
}

class _ConfirmPasswordSheetState extends ConsumerState<ConfirmPasswordSheet> {
  final _password = TextEditingController();

  @override
  void dispose() {
    _password.dispose();
    super.dispose();
  }

  void _confirm() {
    ref
        .read(editProfileControllerProvider.notifier)
        .submit(name: widget.name, email: widget.email, currentPassword: _password.text);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(editProfileControllerProvider);
    ref.listen(editProfileControllerProvider, (previous, next) {
      final finished = previous?.submitting == true && !next.submitting;
      if (finished && next.passwordError == null) Navigator.of(context).pop();
    });
    return Padding(
      // La hoja sube con el teclado.
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 10, 24, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppTokens.inputBorder,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Semantics(
                header: true,
                child: Text(
                  'Confirma tu contraseña',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 24),
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Por seguridad, escribe tu contraseña actual para cambiar tu correo electrónico.',
                style: TextStyle(fontSize: 14, height: 20 / 14, color: AppTokens.textSecondary),
              ),
              const SizedBox(height: 16),
              LabeledField(
                label: 'Contraseña actual',
                controller: _password,
                obscureText: true,
                errorText: state.passwordError,
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.password],
                onSubmitted: (_) => _confirm(),
              ),
              const SizedBox(height: 18),
              PrimaryButton(
                label: 'Confirmar',
                variant: ButtonVariant.dark,
                loading: state.submitting,
                onPressed: _confirm,
              ),
              const SizedBox(height: 10),
              PrimaryButton(
                label: 'Cancelar',
                variant: ButtonVariant.secondary,
                onPressed: state.submitting ? null : () => Navigator.of(context).pop(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
