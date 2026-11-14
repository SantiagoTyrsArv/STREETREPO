import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_error.dart';
import '../../auth/application/auth_providers.dart';
import '../../auth/domain/session.dart';

class DeleteDataState {
  const DeleteDataState({this.submitting = false, this.passwordError, this.error, this.receipt});

  final bool submitting;

  /// Contraseña vacía, incorrecta o demasiados intentos.
  final String? passwordError;

  /// Error que no es de la contraseña (red, servidor).
  final String? error;

  /// Constancia del servidor: la supresión ya ocurrió y la cuenta no existe.
  final DeletionReceipt? receipt;
}

final deleteDataControllerProvider =
    NotifierProvider.autoDispose<DeleteDataController, DeleteDataState>(DeleteDataController.new);

/// Derecho de supresión (Ley 1581). La supresión la hace el servidor; aquí solo se pide y se
/// guarda la constancia. Quien llama cierra la sesión al recibirla.
class DeleteDataController extends Notifier<DeleteDataState> {
  @override
  DeleteDataState build() => const DeleteDataState();

  Future<void> submit(String currentPassword) async {
    // Con la constancia en mano no se vuelve a pedir: la cuenta ya no existe.
    if (state.submitting || state.receipt != null) return;
    if (currentPassword.isEmpty) {
      state = const DeleteDataState(passwordError: 'Escribe tu contraseña actual.');
      return;
    }
    state = const DeleteDataState(submitting: true);
    try {
      final receipt = await ref
          .read(authRepositoryProvider)
          .requestDataDeletion(currentPassword: currentPassword);
      if (ref.mounted) state = DeleteDataState(receipt: receipt);
    } on ApiError catch (e) {
      if (!ref.mounted) return;
      state = switch (e.code) {
        'PASSWORD_CONFIRMATION_FAILED' ||
        'TOO_MANY_LOGIN_ATTEMPTS' => DeleteDataState(passwordError: e.message),
        _ => DeleteDataState(error: e.message),
      };
    } on ApiFailure catch (e) {
      if (ref.mounted) state = DeleteDataState(error: e.message);
    }
  }
}
