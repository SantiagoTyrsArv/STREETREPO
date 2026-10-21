import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/format/formatters.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/primary_button.dart';
import '../../auth/application/session_controller.dart';
import '../../auth/domain/session.dart';

/// Perfil y privacidad (Figma `6:141`), versión mínima de esta entrega: nombre, correo, la
/// política aceptada (enlace de solo lectura) y «Cerrar sesión». Editar los datos, la
/// supresión y las cifras llegan con la siguiente entrega (spec 2.2). El rol no se muestra:
/// el Figma dice «Ciudadana», y el texto no debe suponer el género de nadie.
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _signingOut = false;

  Future<void> _signOut() async {
    setState(() => _signingOut = true);
    // La redirección por sesión lleva a la Bienvenida.
    await ref.read(sessionControllerProvider.notifier).signOut();
    if (mounted) setState(() => _signingOut = false);
  }

  static String _initials(String name) {
    final words = name.trim().split(RegExp(r'\s+')).where((w) => w.isNotEmpty).take(2);
    return words.map((w) => w.characters.first.toUpperCase()).join();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionControllerProvider).value;
    if (session is! SignedIn) return const SizedBox.shrink();
    final user = session.user;
    final theme = Theme.of(context);
    final accepted = user.policyAcceptedAt;
    return SafeArea(
      bottom: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 28, 20, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Semantics(
              header: true,
              child: Text('Perfil', style: theme.textTheme.headlineMedium?.copyWith(fontSize: 28)),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                ExcludeSemantics(
                  child: Container(
                    width: 64,
                    height: 64,
                    alignment: Alignment.center,
                    decoration: const BoxDecoration(color: AppTokens.ink, shape: BoxShape.circle),
                    child: Text(
                      _initials(user.name),
                      style: theme.textTheme.headlineMedium?.copyWith(
                        fontSize: 24,
                        color: AppTokens.amber,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.name,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        user.email,
                        style: const TextStyle(fontSize: 14, color: AppTokens.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            const Text(
              'PRIVACIDAD',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppTokens.textSecondary,
              ),
            ),
            const SizedBox(height: 8),
            Material(
              color: AppTokens.surface,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppTokens.cardRadius),
                side: const BorderSide(color: AppTokens.line),
              ),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () => context.push(AppRoutes.privacyPolicy),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 60),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    child: Row(
                      children: [
                        ExcludeSemantics(child: SvgPicture.asset('assets/icons/shield_small.svg')),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Política de tratamiento de datos',
                                style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
                              ),
                              if (accepted != null)
                                Text(
                                  switch (user.policyVersion) {
                                    final version? =>
                                      'Versión $version · aceptada el ${formatLongDate(accepted)}',
                                    null => 'Aceptada el ${formatLongDate(accepted)}',
                                  },
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: AppTokens.repairedChipText,
                                  ),
                                ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        ExcludeSemantics(child: SvgPicture.asset('assets/icons/chevron.svg')),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),
            PrimaryButton(
              label: 'Cerrar sesión',
              variant: ButtonVariant.secondary,
              loading: _signingOut,
              onPressed: _signOut,
            ),
          ],
        ),
      ),
    );
  }
}
