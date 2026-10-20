import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../../../core/theme/app_tokens.dart';

/// Cabecera del nuevo reporte (Figma `4:78`/`4:84`): cerrar, «Paso N de M» y la barra.
class StepHeader extends StatelessWidget {
  const StepHeader({required this.step, required this.onClose, this.total = 2, super.key});

  final int step;
  final int total;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Semantics(
              button: true,
              label: 'Cerrar el reporte',
              excludeSemantics: true,
              child: InkResponse(
                onTap: onClose,
                radius: AppTokens.minTouchTarget / 2,
                child: SizedBox.square(
                  dimension: AppTokens.minTouchTarget,
                  child: Center(child: SvgPicture.asset('assets/icons/close.svg')),
                ),
              ),
            ),
            const Spacer(),
            Text(
              'Paso $step de $total',
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: AppTokens.textSecondary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ExcludeSemantics(
          child: Row(
            children: [
              for (var i = 1; i <= total; i++) ...[
                if (i > 1) const SizedBox(width: 6),
                Expanded(
                  child: Container(
                    height: 4,
                    decoration: BoxDecoration(
                      color: i <= step ? AppTokens.ink : AppTokens.progressTrack,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}
