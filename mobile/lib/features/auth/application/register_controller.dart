import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_error.dart';
import '../domain/session.dart';
import 'auth_providers.dart';
import 'privacy_policy_providers.dart';
import 'session_controller.dart';

// Límites del backend (`auth/domain/passwords.py`); la validación de aquí es solo de UX.
const int minPasswordLength = 12;
const int maxPasswordLength = 128;
final RegExp _emailPattern = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

class RegisterState {
  const RegisterState({
    this.submitting = false,
    this.nameError,
    this.emailError,
    this.passwordError,
    this.error,
    this.accountCreated = false,
  });

  final bool submitting;
  final String? nameError;
  final String? emailError;
  final String? passwordError;

  /// Error que no es de un campo (política desactualizada, red, límite de intentos).
  final String? error;

  /// La cuenta quedó creada pero no se pudo iniciar sesión: la pantalla lleva a «Ingresar».
  final bool accountCreated;
}

final registerControllerProvider = NotifierProvider.autoDispose<RegisterController, RegisterState>(
  RegisterController.new,
);

class RegisterController extends Notifier<RegisterState> {
  @override
  RegisterState build() => const RegisterState();

  Future<void> submit({
    required String name,
    required String email,
    required String password,
    required PrivacyPolicy policy,
  }) async {
    if (state.submitting) return;
    final invalid = _validate(name.trim(), email.trim(), password);
    if (invalid != null) {
      state = invalid;
      return;
    }
    state = const RegisterState(submitting: true);
    try {
      await ref
          .read(authRepositoryProvider)
          .register(
            name: name.trim(),
            email: email.trim(),
            password: password,
            policyVersion: policy.version,
          );
    } on ApiError catch (e) {
      if (ref.mounted) state = _fromError(e);
      return;
    } on ApiFailure catch (e) {
      if (ref.mounted) state = RegisterState(error: e.message);
      return;
    }
    try {
      await ref
          .read(sessionControllerProvider.notifier)
          .signIn(email: email.trim(), password: password);
      ref.read(policyConsentProvider.notifier).revoke();
    } on ApiFailure {
      if (ref.mounted) state = const RegisterState(accountCreated: true);
    }
  }

  static RegisterState? _validate(String name, String email, String password) {
    final nameError = name.isEmpty ? 'Escribe tu nombre.' : null;
    final emailError = _emailPattern.hasMatch(email) ? null : 'Escribe un correo válido.';
    final passwordError = password.length < minPasswordLength || password.length > maxPasswordLength
        ? 'La contraseña debe tener de $minPasswordLength a $maxPasswordLength caracteres.'
        : null;
    if (nameError == null && emailError == null && passwordError == null) return null;
    return RegisterState(
      nameError: nameError,
      emailError: emailError,
      passwordError: passwordError,
    );
  }

  RegisterState _fromError(ApiError e) {
    switch (e.code) {
      case 'EMAIL_ALREADY_REGISTERED':
        return RegisterState(emailError: e.message);
      case 'WEAK_PASSWORD':
        return RegisterState(passwordError: e.message);
      case 'POLICY_VERSION_OUTDATED':
        // La versión aceptada ya no es la vigente: se recarga y la casilla queda sin marcar.
        ref.invalidate(privacyPolicyProvider);
        return RegisterState(error: e.message);
      case 'VALIDATION_ERROR':
        final fields = _invalidFields(e.details);
        return RegisterState(
          nameError: fields.contains('name') ? 'Revisa tu nombre.' : null,
          emailError: fields.contains('email') ? 'Revisa el correo.' : null,
          passwordError: fields.contains('password') ? 'Revisa la contraseña.' : null,
          error: fields.isEmpty ? e.message : null,
        );
      default:
        return RegisterState(error: e.message);
    }
  }

  static Set<String> _invalidFields(Map<String, dynamic> details) {
    final fields = details['fields'];
    if (fields is! List) return const {};
    return {
      for (final field in fields)
        if (field is Map && field['field'] is String) field['field'] as String,
    };
  }
}
