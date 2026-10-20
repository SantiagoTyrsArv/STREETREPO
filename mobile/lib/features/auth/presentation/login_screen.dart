import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/format/formatters.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/labeled_field.dart';
import '../../../core/widgets/notice_banner.dart';
import '../../../core/widgets/primary_button.dart';
import '../application/login_controller.dart';
import '../application/session_controller.dart';
import '../domain/session.dart';
import 'widgets/auth_header.dart';

/// Iniciar sesión (Figma `2:37`) y su variante «Cuenta bloqueada» (`14:45`).
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({this.createdAccountEmail, super.key});

  /// Correo de una cuenta recién creada con la que no se pudo entrar automáticamente.
  final String? createdAccountEmail;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  late final _email = TextEditingController(text: widget.createdAccountEmail);
  final _password = TextEditingController();

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _submit() {
    FocusScope.of(context).unfocus();
    ref.read(loginControllerProvider.notifier).submit(email: _email.text, password: _password.text);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(loginControllerProvider);
    final expired = switch (ref.watch(sessionControllerProvider)) {
      AsyncData(value: SignedOut(sessionExpired: true)) => true,
      _ => false,
    };
    final lock = state.lockRemaining;
    return Scaffold(
      body: SafeArea(
        child: AutofillGroup(
          child: FillScrollView(
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
            children: [
              const AuthHeader(
                mode: AuthMode.login,
                title: 'Bienvenida de nuevo',
                subtitle: 'Ingresa para reportar y seguir tus reportes.',
              ),
              const SizedBox(height: 16),
              if (lock != null)
                NoticeBanner(
                  title: 'Demasiados intentos fallidos',
                  message:
                      'Por seguridad, espera ${formatWait(lock)} antes de intentarlo de nuevo.',
                )
              else if (state.error != null)
                NoticeBanner(message: state.error!)
              else if (widget.createdAccountEmail != null)
                const NoticeBanner(
                  tone: NoticeTone.info,
                  message: 'Tu cuenta quedó creada. Ingresa con tu correo y contraseña.',
                )
              else if (expired)
                const NoticeBanner(
                  tone: NoticeTone.info,
                  message: 'Tu sesión terminó. Ingresa de nuevo.',
                ),
              const SizedBox(height: 8),
              LabeledField(
                label: 'Correo electrónico',
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                autofillHints: const [AutofillHints.email],
              ),
              const SizedBox(height: 14),
              LabeledField(
                label: 'Contraseña',
                controller: _password,
                obscureText: true,
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.password],
                onSubmitted: (_) => _submit(),
              ),
              const Spacer(),
              const SizedBox(height: 24),
              PrimaryButton(
                label: lock == null ? 'Entrar' : 'Reintentar en ${formatCountdown(lock)}',
                variant: ButtonVariant.dark,
                loading: state.submitting,
                onPressed: lock == null ? _submit : null,
              ),
              const SizedBox(height: 14),
              const SizedBox(
                width: double.infinity,
                child: Text(
                  'Tu sesión se mantiene segura con autenticación por token.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 13, color: AppTokens.textSecondary),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
