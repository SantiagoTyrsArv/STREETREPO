import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/app_back_button.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../core/widgets/notice_banner.dart';
import '../../../core/widgets/primary_button.dart';
import '../../auth/application/session_controller.dart';
import '../../auth/domain/session.dart';
import '../application/edit_profile_controller.dart';
import 'confirm_password_sheet.dart';

/// Perfil · Editar datos (Figma `15:73`): derecho de conocer y actualizar (Ley 1581).
/// Cambiar el correo abre antes la hoja «Confirma tu contraseña» (Figma `16:2`).
class EditProfileScreen extends ConsumerStatefulWidget {
  const EditProfileScreen({super.key});

  @override
  ConsumerState<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends ConsumerState<EditProfileScreen> {
  late final TextEditingController _name;
  late final TextEditingController _email;

  @override
  void initState() {
    super.initState();
    final session = ref.read(sessionControllerProvider).value;
    final user = session is SignedIn ? session.user : null;
    _name = TextEditingController(text: user?.name);
    _email = TextEditingController(text: user?.email);
  }

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    FocusScope.of(context).unfocus();
    final controller = ref.read(editProfileControllerProvider.notifier);
    if (!controller.validate(name: _name.text, email: _email.text)) return;
    if (!controller.emailChanged(_email.text)) {
      await controller.submit(name: _name.text, email: _email.text);
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTokens.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) => ConfirmPasswordSheet(name: _name.text, email: _email.text),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(editProfileControllerProvider);
    ref.listen(editProfileControllerProvider, (previous, next) {
      if (next.saved && previous?.saved != true) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('Tus datos quedaron actualizados.')));
        context.pop();
      }
    });
    return Scaffold(
      body: SafeArea(
        child: FillScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          children: [
            AppBackButton(onPressed: () => context.pop()),
            const SizedBox(height: 12),
            Semantics(
              header: true,
              child: Text(
                'Editar datos',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontSize: 28),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Actualiza tu nombre o tu correo electrónico.',
              style: TextStyle(fontSize: 15, color: AppTokens.textSecondary),
            ),
            const SizedBox(height: 20),
            if (state.error != null) ...[
              NoticeBanner(message: state.error!),
              const SizedBox(height: 14),
            ],
            LabeledField(
              label: 'Nombre',
              controller: _name,
              errorText: state.nameError,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.name],
            ),
            const SizedBox(height: 14),
            LabeledField(
              label: 'Correo electrónico',
              controller: _email,
              errorText: state.emailError,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.done,
              autofillHints: const [AutofillHints.email],
            ),
            const SizedBox(height: 16),
            const NoticeBanner(
              tone: NoticeTone.info,
              title: 'Cambiar el correo requiere tu contraseña',
              message: 'Te la pediremos antes de guardar.',
            ),
            const Spacer(),
            const SizedBox(height: 24),
            PrimaryButton(
              label: 'Guardar cambios',
              variant: ButtonVariant.dark,
              loading: state.submitting,
              onPressed: _save,
            ),
            const SizedBox(height: 10),
            PrimaryButton(
              label: 'Cancelar',
              variant: ButtonVariant.secondary,
              onPressed: state.submitting ? null : () => context.pop(),
            ),
          ],
        ),
      ),
    );
  }
}
