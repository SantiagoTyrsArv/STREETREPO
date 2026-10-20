import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/consent_checkbox.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../core/widgets/notice_banner.dart';
import '../../../core/widgets/primary_button.dart';
import '../application/privacy_policy_providers.dart';
import '../application/register_controller.dart';
import '../domain/session.dart';
import 'widgets/auth_header.dart';

/// Registro con la política de datos (Figma `14:3`).
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _submit(PrivacyPolicy policy) {
    FocusScope.of(context).unfocus();
    ref
        .read(registerControllerProvider.notifier)
        .submit(name: _name.text, email: _email.text, password: _password.text, policy: policy);
  }

  @override
  Widget build(BuildContext context) {
    ref.listen(registerControllerProvider, (_, next) {
      if (next.accountCreated) context.pushReplacement(AppRoutes.login, extra: _email.text.trim());
    });
    final state = ref.watch(registerControllerProvider);
    final policy = ref.watch(privacyPolicyProvider);
    final acceptedVersion = ref.watch(policyConsentProvider);
    final current = policy.value;
    final accepted = current != null && acceptedVersion == current.version;

    return Scaffold(
      body: SafeArea(
        child: AutofillGroup(
          child: FillScrollView(
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
            children: [
              const AuthHeader(
                mode: AuthMode.register,
                title: 'Crea tu cuenta',
                subtitle: 'Reporta daños viales en Pasto y sigue su atención.',
              ),
              const SizedBox(height: 18),
              if (state.error != null) ...[
                NoticeBanner(message: state.error!),
                const SizedBox(height: 14),
              ],
              LabeledField(
                label: 'Nombre',
                controller: _name,
                errorText: state.nameError,
                keyboardType: TextInputType.name,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.name],
              ),
              const SizedBox(height: 14),
              LabeledField(
                label: 'Correo electrónico',
                controller: _email,
                errorText: state.emailError,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.email],
              ),
              const SizedBox(height: 14),
              LabeledField(
                label: 'Contraseña',
                controller: _password,
                obscureText: true,
                errorText: state.passwordError,
                helperText: 'De $minPasswordLength a $maxPasswordLength caracteres.',
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.newPassword],
              ),
              const SizedBox(height: 16),
              _Consent(policy: policy, accepted: accepted),
              const Spacer(),
              const SizedBox(height: 24),
              PrimaryButton(
                label: 'Crear cuenta',
                variant: ButtonVariant.dark,
                loading: state.submitting,
                onPressed: accepted ? () => _submit(current) : null,
              ),
              const SizedBox(height: 10),
              const SizedBox(
                width: double.infinity,
                child: Text(
                  'Guardamos la fecha y la versión de tu consentimiento.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: AppTokens.textSecondary),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Casilla de la política con su versión vigente y el enlace para leerla.
class _Consent extends ConsumerWidget {
  const _Consent({required this.policy, required this.accepted});

  final AsyncValue<PrivacyPolicy> policy;
  final bool accepted;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    switch (policy) {
      case AsyncData(:final value):
        final consent = ref.read(policyConsentProvider.notifier);
        return ConsentCheckbox(
          value: accepted,
          onChanged: (checked) => checked ? consent.accept(value.version) : consent.revoke(),
          label:
              'Acepto la política de tratamiento de datos personales (versión ${value.version}), '
              'conforme a la Ley 1581 de 2012.',
          fontSize: 13,
          check: const Icon(Icons.check_rounded, size: 16, color: AppTokens.surface),
          below: TextButton(
            onPressed: () => context.push(AppRoutes.privacyPolicy),
            style: TextButton.styleFrom(
              padding: EdgeInsets.zero,
              minimumSize: const Size(0, AppTokens.minTouchTarget),
              alignment: Alignment.centerLeft,
              foregroundColor: AppTokens.link,
              textStyle: Theme.of(context).textTheme.labelLarge?.copyWith(fontSize: 13),
            ),
            child: const Text('Leer la política'),
          ),
        );
      case AsyncError():
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const NoticeBanner(
              message: 'No pudimos cargar la política de datos. Sin ella no puedes registrarte.',
            ),
            TextButton(
              onPressed: () => ref.invalidate(privacyPolicyProvider),
              style: TextButton.styleFrom(foregroundColor: AppTokens.link),
              child: const Text('Reintentar'),
            ),
          ],
        );
      default:
        return const Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: Text(
            'Cargando la política de datos…',
            style: TextStyle(fontSize: 13, color: AppTokens.textSecondary),
          ),
        );
    }
  }
}
