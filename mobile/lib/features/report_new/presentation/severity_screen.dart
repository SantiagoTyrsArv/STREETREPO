import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';

import '../../../core/domain/report_enums.dart';
import '../../../core/format/formatters.dart';
import '../../../core/routing/app_router.dart';
import '../../../core/theme/app_tokens.dart';
import '../../../core/widgets/fill_scroll_view.dart';
import '../../../core/widgets/notice_banner.dart';
import '../../../core/widgets/primary_button.dart';
import '../../../core/widgets/severity_chip.dart';
import '../application/report_draft_controller.dart';
import '../application/submit_report_controller.dart';
import '../domain/report_draft.dart';
import '../domain/submit_outcome.dart';
import 'submit_navigation.dart';
import 'widgets/step_header.dart';

/// Nuevo reporte, paso 2 de 2: severidad y descripción opcional (Figma `5:2`).
///
/// El resumen muestra las coordenadas: la dirección la calcula el servidor al crear el
/// reporte (aparece en «Reporte enviado»).
class SeverityScreen extends ConsumerStatefulWidget {
  const SeverityScreen({super.key});

  @override
  ConsumerState<SeverityScreen> createState() => _SeverityScreenState();
}

class _SeverityScreenState extends ConsumerState<SeverityScreen> {
  late final TextEditingController _description;
  SubmitFailed? _failure;

  static const _descriptions = {
    Severity.low: 'Grieta o deterioro leve. No afecta la circulación.',
    Severity.medium: 'Bache que obliga a maniobrar o reducir la velocidad.',
    Severity.high: 'Hueco profundo, peligroso para vehículos y peatones.',
  };

  @override
  void initState() {
    super.initState();
    _description = TextEditingController(text: ref.read(reportDraftProvider).description);
  }

  @override
  void dispose() {
    _description.dispose();
    super.dispose();
  }

  void _back() => context.canPop() ? context.pop() : context.go(AppRoutes.newReport);

  Future<void> _send() async {
    setState(() => _failure = null);
    final outcome = await ref.read(submitReportProvider.notifier).submit();
    if (!mounted) return;
    if (!showSubmitOutcome(context, outcome)) setState(() => _failure = outcome as SubmitFailed);
  }

  @override
  Widget build(BuildContext context) {
    final draft = ref.watch(reportDraftProvider);
    final busy = ref.watch(submitReportProvider.select((s) => s.busy));
    final failure = _failure;
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: FillScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            StepHeader(step: 2, back: true, onClose: _back),
            const SizedBox(height: 20),
            Semantics(
              header: true,
              child: Text(
                '¿Qué tan grave es el daño?',
                style: theme.textTheme.headlineMedium?.copyWith(fontSize: 26, height: 28 / 26),
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              'Elige la opción que mejor lo describa.',
              style: TextStyle(fontSize: 14, color: AppTokens.textSecondary),
            ),
            const SizedBox(height: 16),
            for (final severity in Severity.values) ...[
              if (severity != Severity.low) const SizedBox(height: 10),
              _SeverityOption(
                severity: severity,
                description: _descriptions[severity]!,
                selected: draft.severity == severity,
                onTap: busy
                    ? null
                    : () => ref.read(reportDraftProvider.notifier).setSeverity(severity),
              ),
            ],
            const SizedBox(height: 16),
            _DescriptionField(
              controller: _description,
              enabled: !busy,
              onChanged: ref.read(reportDraftProvider.notifier).setDescription,
            ),
            const Spacer(),
            const SizedBox(height: 16),
            if (failure != null) ...[
              NoticeBanner(title: 'No se pudo enviar el reporte', message: failure.message),
              const SizedBox(height: 12),
            ],
            _Summary(fix: draft.fix),
            const SizedBox(height: 12),
            PrimaryButton(
              label: failure?.retryable ?? false ? 'Reintentar el envío' : 'Enviar reporte',
              variant: ButtonVariant.dark,
              loading: busy,
              onPressed: draft.severity != null && draft.hasEvidence ? _send : null,
            ),
          ],
        ),
      ),
    );
  }
}

class _SeverityOption extends StatelessWidget {
  const _SeverityOption({
    required this.severity,
    required this.description,
    required this.selected,
    required this.onTap,
  });

  final Severity severity;
  final String description;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      inMutuallyExclusiveGroup: true,
      checked: selected,
      button: true,
      label: 'Severidad ${severity.label.toLowerCase()}. $description',
      excludeSemantics: true,
      child: Material(
        color: selected ? AppTokens.surface : AppTokens.optionSurface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppTokens.cardRadius),
          // El borde transparente evita que la opción cambie de tamaño al elegirla.
          side: BorderSide(color: selected ? AppTokens.ink : Colors.transparent, width: 2),
        ),
        child: InkWell(
          onTap: onTap,
          customBorder: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTokens.cardRadius),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(color: severityColor(severity), shape: BoxShape.circle),
                  child: Text(
                    severity.label.substring(0, 1),
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                      color: AppTokens.surface,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        severity.label,
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        description,
                        style: const TextStyle(
                          fontSize: 13,
                          height: 18 / 13,
                          color: AppTokens.optionText,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 14),
                _Radio(selected: selected),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Radio extends StatelessWidget {
  const _Radio({required this.selected});

  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 22,
      height: 22,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: AppTokens.ink, width: 2),
      ),
      child: selected
          ? Container(
              width: 12,
              height: 12,
              decoration: const BoxDecoration(color: AppTokens.ink, shape: BoxShape.circle),
            )
          : null,
    );
  }
}

class _DescriptionField extends StatelessWidget {
  const _DescriptionField({
    required this.controller,
    required this.enabled,
    required this.onChanged,
  });

  static const _label = 'Descripción (opcional)';

  final TextEditingController controller;
  final bool enabled;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const ExcludeSemantics(
          child: Text(_label, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
        ),
        const SizedBox(height: 6),
        Semantics(
          label: _label,
          child: TextField(
            controller: controller,
            enabled: enabled,
            onChanged: onChanged,
            minLines: 3,
            maxLines: 5,
            maxLength: descriptionMaxLength,
            keyboardType: TextInputType.multiline,
            textCapitalization: TextCapitalization.sentences,
            style: const TextStyle(fontSize: 15, height: 21 / 15, color: AppTokens.ink),
            buildCounter: (context, {required currentLength, required isFocused, maxLength}) =>
                Text(
                  '$currentLength/$maxLength',
                  semanticsLabel: '$currentLength de $maxLength caracteres',
                  style: const TextStyle(fontSize: 12, color: AppTokens.textSecondary),
                ),
          ),
        ),
      ],
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({required this.fix});

  final GeoFix? fix;

  @override
  Widget build(BuildContext context) {
    final current = fix;
    final place = current == null
        ? 'Sin ubicación'
        : formatCoordinates(current.latitude, current.longitude);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppTokens.surface,
        border: Border.all(color: AppTokens.line),
        borderRadius: BorderRadius.circular(AppTokens.fieldRadius),
      ),
      child: Row(
        children: [
          ExcludeSemantics(child: SvgPicture.asset('assets/icons/pin_small.svg')),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              '$place · 1 foto',
              style: const TextStyle(fontSize: 13, color: AppTokens.cardText),
            ),
          ),
        ],
      ),
    );
  }
}
