import 'nearby_report.dart';

/// Cómo terminó un intento de enviar o confirmar el reporte; cada caso tiene su pantalla.
sealed class SubmitOutcome {
  const SubmitOutcome();
}

final class Sent extends SubmitOutcome {
  const Sent(this.report);

  final CreatedReport report;
}

/// Se confirmó [report] en lugar de crear otro; [confirmations] es el total actual.
final class Confirmed extends SubmitOutcome {
  const Confirmed(this.report, this.confirmations);

  final NearbyReport report;
  final int confirmations;
}

/// Hay reportes activos a 25 m: el ciudadano decide si confirmar uno o crear el suyo.
final class PossibleDuplicates extends SubmitOutcome {
  const PossibleDuplicates(this.candidates);

  final List<NearbyReport> candidates;
}

final class OutsideServiceArea extends SubmitOutcome {
  const OutsideServiceArea();
}

final class RateLimited extends SubmitOutcome {
  const RateLimited(this.retryAfter);

  final Duration retryAfter;
}

/// El servidor no aceptó la foto: hay que tomar otra.
final class PhotoRejected extends SubmitOutcome {
  const PhotoRejected(this.message);

  final String message;
}

/// No se pudo completar; si [retryable], reintentar con el mismo borrador tiene sentido.
final class SubmitFailed extends SubmitOutcome {
  const SubmitFailed(this.message, {required this.retryable});

  final String message;
  final bool retryable;
}
