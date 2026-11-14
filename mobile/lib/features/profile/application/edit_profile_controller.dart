import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_error.dart';
import '../../auth/application/auth_providers.dart';
import '../../auth/application/register_controller.dart' show emailPattern;
import '../../auth/application/session_controller.dart';
import '../../auth/domain/session.dart';

class EditProfileState {
  const EditProfileState({
    this.submitting = false,
    this.nameError,
    this.emailError,
    this.passwordError,
    this.error,
    this.saved = false,
  });

  final bool submitting;
  final String? nameError;
  final String? emailError;

  /// Fallo de la confirmación de contraseña (incorrecta o demasiados intentos): se muestra
  /// en la hoja «Confirma tu contraseña».
  final String? passwordError;

  /// Error que no es de un campo (red, servidor).
  final String? error;

  /// Los datos quedaron guardados: la pantalla vuelve al Perfil.
  final bool saved;
}

final editProfileControllerProvider =
    NotifierProvider.autoDispose<EditProfileController, EditProfileState>(
      EditProfileController.new,
    );

/// «Conocer y actualizar mis datos» (Ley 1581). La validación de aquí es solo de UX: el
/// servidor vuelve a validar y exige la contraseña para cambiar el correo.
class EditProfileController extends Notifier<EditProfileState> {
  @override
  EditProfileState build() => const EditProfileState();

  UserProfile? get _user => switch (ref.read(sessionControllerProvider)) {
    AsyncData(value: SignedIn(:final user)) => user,
    _ => null,
  };

  /// Revisa los campos antes de pedir la contraseña; deja los errores en el estado.
  bool validate({required String name, required String email}) {
    final nameError = name.trim().isEmpty ? 'Escribe tu nombre.' : null;
    final emailError = emailPattern.hasMatch(email.trim()) ? null : 'Escribe un correo válido.';
    state = EditProfileState(nameError: nameError, emailError: emailError);
    return nameError == null && emailError == null;
  }

  /// Cambiar el correo exige la contraseña actual.
  bool emailChanged(String email) => email.trim() != _user?.email;

  Future<void> submit({
    required String name,
    required String email,
    String? currentPassword,
  }) async {
    final user = _user;
    if (state.submitting || user == null) return;
    if (!validate(name: name, email: email)) return;
    final newName = name.trim() == user.name ? null : name.trim();
    final newEmail = email.trim() == user.email ? null : email.trim();
    if (newName == null && newEmail == null) {
      // Nada cambió: no hay nada que enviar.
      state = const EditProfileState(saved: true);
      return;
    }
    if (newEmail != null && (currentPassword == null || currentPassword.isEmpty)) {
      state = const EditProfileState(passwordError: 'Escribe tu contraseña actual.');
      return;
    }
    state = const EditProfileState(submitting: true);
    try {
      final updated = await ref
          .read(authRepositoryProvider)
          .updateProfile(
            name: newName,
            email: newEmail,
            currentPassword: newEmail == null ? null : currentPassword,
          );
      ref.read(sessionControllerProvider.notifier).userUpdated(updated);
      if (ref.mounted) state = const EditProfileState(saved: true);
    } on ApiError catch (e) {
      if (ref.mounted) state = _fromError(e);
    } on ApiFailure catch (e) {
      if (ref.mounted) state = EditProfileState(error: e.message);
    }
  }

  static EditProfileState _fromError(ApiError e) {
    switch (e.code) {
      case 'EMAIL_ALREADY_REGISTERED':
        return EditProfileState(emailError: e.message);
      case 'PASSWORD_CONFIRMATION_FAILED' ||
          'PASSWORD_CONFIRMATION_REQUIRED' ||
          'TOO_MANY_LOGIN_ATTEMPTS':
        return EditProfileState(passwordError: e.message);
      case 'VALIDATION_ERROR':
        final fields = _invalidFields(e.details);
        return EditProfileState(
          nameError: fields.contains('name') ? 'Revisa tu nombre.' : null,
          emailError: fields.contains('email') ? 'Revisa el correo.' : null,
          error: fields.contains('name') || fields.contains('email') ? null : e.message,
        );
      default:
        return EditProfileState(error: e.message);
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
