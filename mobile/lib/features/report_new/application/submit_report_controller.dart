import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../../core/network/api_error.dart';
import '../../auth/application/auth_providers.dart';
import '../../auth/application/session_controller.dart';
import '../data/http_new_report_repository.dart';
import '../domain/nearby_report.dart';
import '../domain/new_report_repository.dart';
import '../domain/submit_outcome.dart';
import 'report_draft_controller.dart';

final newReportRepositoryProvider = Provider<NewReportRepository>(
  (ref) => HttpNewReportRepository(ref.watch(apiClientProvider)),
);

/// Genera la `Idempotency-Key` de cada envío (UUID v4).
final idempotencyKeyFactoryProvider = Provider<String Function()>((ref) => const Uuid().v4);

/// Esperas entre los intentos automáticos ante un fallo de red o un 5xx (propuesta 55): tres
/// intentos en total antes de ofrecer «Reintentar».
const List<Duration> submitRetryDelays = [Duration(seconds: 2), Duration(seconds: 4)];

/// Espera entre intentos; las pruebas la reemplazan para no dormir.
final submitRetryWaitProvider = Provider<Future<void> Function(Duration)>(
  (ref) => Future<void>.delayed,
);

/// Espera que se muestra si un 429 no trae `Retry-After` ni `retry_after_s`.
const Duration _fallbackRetryAfter = Duration(minutes: 1);

class SubmitState {
  const SubmitState({this.busy = false, this.outcome});

  /// Hay un envío o una confirmación en curso.
  final bool busy;

  /// Resultado del último intento; las pantallas de resultado lo leen de aquí.
  final SubmitOutcome? outcome;
}

/// Envío del borrador y confirmación de un duplicado. Depende del ciudadano en sesión, como
/// el borrador (propuesta 56).
final submitReportProvider = NotifierProvider<SubmitReportController, SubmitState>(
  SubmitReportController.new,
);

class SubmitReportController extends Notifier<SubmitState> {
  @override
  SubmitState build() {
    ref.watch(currentUserIdProvider);
    return const SubmitState();
  }

  NewReportRepository get _repository => ref.read(newReportRepositoryProvider);

  ReportDraftController get _draft => ref.read(reportDraftProvider.notifier);

  /// Envía el borrador. La primera vez genera la clave y consulta los reportes cercanos; si
  /// la clave ya existe es un reintento y va directo al envío con la misma clave: el servidor
  /// vuelve a buscar duplicados y respondería 409 (propuesta 55).
  Future<SubmitOutcome> submit() {
    final firstAttempt = ref.read(reportDraftProvider).idempotencyKey == null;
    if (firstAttempt) _draft.setIdempotencyKey(ref.read(idempotencyKeyFactoryProvider)());
    return _run((attempt) async {
      if (firstAttempt && attempt == 0) {
        final fix = ref.read(reportDraftProvider).fix;
        if (fix == null) throw StateError('El borrador no tiene ubicación');
        final candidates = await _repository.nearby(fix);
        if (candidates.isNotEmpty) return PossibleDuplicates(candidates);
      }
      return _create(createAnyway: false);
    });
  }

  /// El ciudadano vio los posibles duplicados y decide crear el suyo.
  Future<SubmitOutcome> createAnyway() => _run((_) => _create(createAnyway: true));

  /// Confirma [report] en lugar de crear otro (HU-16).
  Future<SubmitOutcome> confirm(NearbyReport report) => _run((_) async {
    try {
      return Confirmed(report, await _repository.confirm(report.id));
    } on ApiError catch (e) {
      // Ya lo había confirmado (p. ej. una respuesta perdida): se considera hecho.
      if (e.code == 'CONFIRMATION_ALREADY_EXISTS') return Confirmed(report, report.confirmations);
      rethrow;
    }
  });

  Future<SubmitOutcome> _create({required bool createAnyway}) async {
    final draft = ref.read(reportDraftProvider);
    final key = draft.idempotencyKey ?? ref.read(idempotencyKeyFactoryProvider)();
    if (draft.idempotencyKey == null) _draft.setIdempotencyKey(key);
    return Sent(await _repository.create(draft, idempotencyKey: key, createAnyway: createAnyway));
  }

  /// Ejecuta [body] con los reintentos automáticos y deja el resultado en el estado.
  Future<SubmitOutcome> _run(Future<SubmitOutcome> Function(int attempt) body) async {
    if (state.busy) throw StateError('Ya hay un envío en curso');
    state = SubmitState(busy: true, outcome: state.outcome);
    final wait = ref.read(submitRetryWaitProvider);
    SubmitOutcome outcome;
    for (var attempt = 0; ; attempt++) {
      try {
        outcome = await body(attempt);
        break;
      } on ApiFailure catch (failure) {
        final canRetry = attempt < submitRetryDelays.length && _isTransient(failure);
        if (!canRetry) {
          outcome = _outcomeOf(failure);
          break;
        }
        await wait(submitRetryDelays[attempt]);
        if (!ref.mounted) return _outcomeOf(failure);
      }
    }
    if (!ref.mounted) return outcome;
    if (outcome is Sent || outcome is Confirmed) _draft.reset();
    state = SubmitState(outcome: outcome);
    return outcome;
  }

  static bool _isTransient(ApiFailure failure) => switch (failure) {
    NetworkFailure() => true,
    ApiError(:final status) => status >= 500,
    UnexpectedFailure() => false,
  };

  SubmitOutcome _outcomeOf(ApiFailure failure) {
    switch (failure) {
      case NetworkFailure() || UnexpectedFailure():
        return SubmitFailed(failure.message, retryable: true);
      case ApiError(status: final status) when status >= 500:
        return SubmitFailed(failure.message, retryable: true);
      case ApiError(status: 429):
        return RateLimited(failure.retryAfter ?? _retryAfterFromDetails(failure.details));
      case ApiError(code: 'REPORT_DUPLICATE_NEARBY'):
        try {
          return PossibleDuplicates(parseNearbyItems(failure.details['items']));
        } on FormatException {
          return SubmitFailed(failure.message, retryable: false);
        }
      case ApiError(code: 'LOCATION_OUTSIDE_SERVICE_AREA'):
        return const OutsideServiceArea();
      case ApiError(code: 'PHOTO_TOO_LARGE' || 'PHOTO_UNSUPPORTED_TYPE' || 'PHOTO_INVALID'):
        return PhotoRejected(failure.message);
      case ApiError(code: 'IDEMPOTENCY_KEY_REUSED'):
        // No debería pasar (cada cambio anula la clave); si pasa, el siguiente envío es nuevo.
        _draft.clearIdempotencyKey();
        return SubmitFailed(failure.message, retryable: true);
      case ApiError():
        return SubmitFailed(failure.message, retryable: false);
    }
  }

  static Duration _retryAfterFromDetails(Map<String, dynamic> details) {
    final seconds = details['retry_after_s'];
    return seconds is int ? Duration(seconds: seconds) : _fallbackRetryAfter;
  }
}
