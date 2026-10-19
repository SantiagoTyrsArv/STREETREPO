import 'package:flutter/material.dart';

import '../theme/app_tokens.dart';
import 'primary_button.dart';

/// Estados completos de cada pantalla (guía 10.3): cargando, vacío y error con reintento.
class LoadingView extends StatelessWidget {
  const LoadingView({this.label = 'Cargando…', super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Semantics(
        label: label,
        child: const CircularProgressIndicator(color: AppTokens.ink),
      ),
    );
  }
}

class EmptyView extends StatelessWidget {
  const EmptyView({required this.title, this.message, this.action, super.key});

  final String title;
  final String? message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return _Centered(
      children: [
        Text(title, style: theme.textTheme.headlineSmall, textAlign: TextAlign.center),
        if (message != null) ...[
          const SizedBox(height: 8),
          Text(message!, style: theme.textTheme.bodySmall, textAlign: TextAlign.center),
        ],
        if (action != null) ...[const SizedBox(height: 20), action!],
      ],
    );
  }
}

class ErrorView extends StatelessWidget {
  const ErrorView({required this.message, required this.onRetry, super.key});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return _Centered(
      children: [
        Text(message, style: Theme.of(context).textTheme.bodyLarge, textAlign: TextAlign.center),
        const SizedBox(height: 20),
        PrimaryButton(label: 'Reintentar', onPressed: onRetry, variant: ButtonVariant.outline),
      ],
    );
  }
}

class _Centered extends StatelessWidget {
  const _Centered({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppTokens.screenPadding + 8),
        child: Column(mainAxisSize: MainAxisSize.min, children: children),
      ),
    );
  }
}
