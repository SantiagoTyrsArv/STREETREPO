import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_error.dart';
import 'session_controller.dart';

/// Espera si el servidor responde 429 sin `Retry-After`.
const Duration _defaultLockout = Duration(minutes: 1);

class LoginState {
  const LoginState({this.submitting = false, this.error, this.lockRemaining});

  final bool submitting;

  /// Mensaje del servidor (ya en español) o de red.
  final String? error;

  /// Tiempo que falta para poder intentar de nuevo tras demasiados intentos (429).
  final Duration? lockRemaining;

  bool get locked => lockRemaining != null;
}

final loginControllerProvider = NotifierProvider.autoDispose<LoginController, LoginState>(
  LoginController.new,
);

class LoginController extends Notifier<LoginState> {
  Timer? _ticker;

  @override
  LoginState build() {
    ref.onDispose(() => _ticker?.cancel());
    return const LoginState();
  }

  Future<void> submit({required String email, required String password}) async {
    if (state.submitting || state.locked) return;
    state = const LoginState(submitting: true);
    try {
      await ref
          .read(sessionControllerProvider.notifier)
          .signIn(email: email.trim(), password: password);
      if (ref.mounted) state = const LoginState();
    } on ApiError catch (e) {
      if (!ref.mounted) return;
      if (e.status == 429) {
        _lock(e.retryAfter ?? _defaultLockout);
      } else {
        state = LoginState(error: e.message);
      }
    } on ApiFailure catch (e) {
      if (ref.mounted) state = LoginState(error: e.message);
    }
  }

  void _lock(Duration duration) {
    state = LoginState(lockRemaining: duration);
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(seconds: 1), (timer) {
      final left = state.lockRemaining! - const Duration(seconds: 1);
      if (left > Duration.zero) {
        state = LoginState(lockRemaining: left);
      } else {
        timer.cancel();
        state = const LoginState();
      }
    });
  }
}
