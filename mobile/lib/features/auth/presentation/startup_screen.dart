import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_error.dart';
import '../../../core/widgets/state_views.dart';
import '../application/session_controller.dart';

/// Mientras se recupera la sesión guardada. Si no hay red, ofrece reintentar sin borrarla.
class StartupScreen extends ConsumerWidget {
  const StartupScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);
    return Scaffold(
      body: SafeArea(
        child: session.hasError
            ? ErrorView(
                message: session.error is ApiFailure
                    ? (session.error! as ApiFailure).message
                    : const UnexpectedFailure().message,
                onRetry: () => ref.read(sessionControllerProvider.notifier).restore(),
              )
            : const LoadingView(label: 'Abriendo Street Repo…'),
      ),
    );
  }
}
