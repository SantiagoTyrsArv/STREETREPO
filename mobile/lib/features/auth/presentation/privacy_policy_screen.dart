import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/platform/url_opener.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/app_back_button.dart';
import '../../../core/widgets/consent_checkbox.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/primary_button.dart';
import '../../../core/widgets/state_views.dart';
import '../application/privacy_policy_providers.dart';
import '../domain/session.dart';

/// Política de datos, Ley 1581 (Figma `2:66`). Acepta la versión vigente y vuelve al registro.
class PrivacyPolicyScreen extends ConsumerWidget {
  const PrivacyPolicyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      body: SafeArea(
        child: switch (ref.watch(privacyPolicyProvider)) {
          AsyncData(:final value) => _PolicyBody(policy: value),
          AsyncError() => ErrorView(
            message: 'No pudimos cargar la política de datos. Revisa tu conexión.',
            onRetry: () => ref.invalidate(privacyPolicyProvider),
          ),
          _ => const LoadingView(label: 'Cargando la política de datos…'),
        },
      ),
    );
  }
}

class _PolicyBody extends ConsumerStatefulWidget {
  const _PolicyBody({required this.policy});

  final PrivacyPolicy policy;

  @override
  ConsumerState<_PolicyBody> createState() => _PolicyBodyState();
}

class _PolicyBodyState extends ConsumerState<_PolicyBody> {
  late bool _checked = ref.read(policyConsentProvider) == widget.policy.version;

  void _back() => context.canPop() ? context.pop() : context.go(AppRoutes.register);

  void _accept() {
    ref.read(policyConsentProvider.notifier).accept(widget.policy.version);
    _back();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final url = widget.policy.url;
    return FillScrollView(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
      children: [
        AppBackButton(onPressed: _back),
        const SizedBox(height: 8),
        Container(
          width: 52,
          height: 52,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppTokens.amberSoft,
            borderRadius: BorderRadius.circular(AppTokens.buttonRadius),
          ),
          child: ExcludeSemantics(child: SvgPicture.asset('assets/icons/shield.svg')),
        ),
        const SizedBox(height: 16),
        Semantics(
          header: true,
          child: Text(
            'Tu información, con tu permiso',
            style: theme.textTheme.headlineMedium?.copyWith(height: 30 / 28),
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Antes de usar la app, conoce cómo tratamos tus datos personales conforme a la '
          'Ley 1581 de 2012.',
          style: TextStyle(fontSize: 15, height: 22 / 15, color: AppTokens.textSecondary),
        ),
        const SizedBox(height: 20),
        const _PolicyCard(
          title: 'Qué recopilamos',
          body:
              'Nombre, correo, la ubicación y la foto de cada daño que reportas, y tus '
              'confirmaciones de reportes.',
        ),
        const SizedBox(height: 10),
        const _PolicyCard(
          title: 'Para qué lo usamos',
          body:
              'Registrar y priorizar daños viales, y darte seguimiento al estado de tus reportes.',
        ),
        const SizedBox(height: 10),
        const _PolicyCard(
          title: 'Tus derechos',
          body:
              'Puedes conocer, actualizar, rectificar y solicitar la supresión de tus datos desde '
              'tu perfil.',
        ),
        const SizedBox(height: 12),
        // Versión y texto completo: el Figma no los muestra; los exige el consentimiento informado.
        Text(
          'Versión ${widget.policy.version} de la política.',
          style: const TextStyle(fontSize: 13, color: AppTokens.textSecondary),
        ),
        if (url != null)
          TextButton(
            onPressed: () => ref.read(urlOpenerProvider)(url),
            style: TextButton.styleFrom(
              padding: EdgeInsets.zero,
              minimumSize: const Size(0, AppTokens.minTouchTarget),
              foregroundColor: AppTokens.link,
              textStyle: Theme.of(context).textTheme.labelLarge?.copyWith(fontSize: 14),
            ),
            child: const Text('Leer la política completa'),
          )
        else
          const Text(
            'El texto completo aún no está publicado.',
            style: TextStyle(fontSize: 13, color: AppTokens.textSecondary),
          ),
        const Spacer(),
        const SizedBox(height: 24),
        ConsentCheckbox(
          value: _checked,
          onChanged: (checked) => setState(() => _checked = checked),
          size: 26,
          radius: 7,
          check: SvgPicture.asset('assets/icons/check_small.svg'),
          label: 'He leído y acepto la política de tratamiento de datos personales de Street Repo.',
        ),
        const SizedBox(height: 18),
        PrimaryButton(
          label: 'Aceptar y continuar',
          variant: ButtonVariant.dark,
          onPressed: _checked ? _accept : null,
        ),
      ],
    );
  }
}

class _PolicyCard extends StatelessWidget {
  const _PolicyCard({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppTokens.surface,
        border: Border.all(color: AppTokens.line),
        borderRadius: BorderRadius.circular(AppTokens.buttonRadius),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(
            body,
            style: const TextStyle(fontSize: 14, height: 20 / 14, color: AppTokens.cardText),
          ),
        ],
      ),
    );
  }
}
