import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_router.dart';
import '../domain/submit_outcome.dart';

/// Lleva a la pantalla de cada resultado. Devuelve false si el resultado se muestra en la
/// pantalla actual (un fallo que se explica en línea).
bool showSubmitOutcome(BuildContext context, SubmitOutcome outcome) {
  switch (outcome) {
    case Sent() || Confirmed():
      // El reporte terminó: no se vuelve a los pasos con «atrás».
      context.go(AppRoutes.newReportSent);
    case PossibleDuplicates():
      context.push(AppRoutes.newReportDuplicates);
    case OutsideServiceArea():
      context.push(AppRoutes.newReportOutsideArea);
    case RateLimited():
      context.push(AppRoutes.newReportRateLimited);
    case PhotoRejected():
      context.push(AppRoutes.newReportPhotoRejected);
    case SubmitFailed():
      return false;
  }
  return true;
}
