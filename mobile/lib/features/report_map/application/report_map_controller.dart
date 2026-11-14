import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/domain/report_enums.dart';
import '../../../core/network/api_error.dart';
import '../../auth/application/auth_providers.dart';
import '../../auth/application/session_controller.dart';
import '../../my_reports/application/my_reports_controller.dart';
import '../../report_new/application/submit_report_controller.dart';
import '../data/http_report_map_repository.dart';
import '../domain/map_report.dart';
import '../domain/report_map_repository.dart';

final reportMapRepositoryProvider = Provider<ReportMapRepository>(
  (ref) => HttpReportMapRepository(ref.watch(apiClientProvider)),
);

class ReportMapState {
  const ReportMapState({
    this.area,
    this.filter,
    this.reports = const [],
    this.truncated = false,
    this.loading = false,
    this.loaded = false,
    this.failure,
    this.selectedId,
    this.confirming = false,
    this.confirmError,
    this.confirmedNotice = false,
  });

  /// Área visible que se pidió por última vez; null hasta que el mapa está listo.
  final MapArea? area;

  /// Estado elegido en los filtros; null es «Todos».
  final ReportStatus? filter;

  /// Lo último que respondió el servidor. Se conserva si una consulta posterior falla.
  final List<MapReport> reports;
  final bool truncated;
  final bool loading;

  /// Ya hubo al menos una respuesta del servidor (distingue «vacío» de «aún no cargó»).
  final bool loaded;
  final ApiFailure? failure;
  final String? selectedId;
  final bool confirming;
  final String? confirmError;

  /// La última confirmación quedó registrada: la pantalla lo avisa una vez.
  final bool confirmedNotice;

  MapReport? get selected {
    for (final report in reports) {
      if (report.id == selectedId) return report;
    }
    return null;
  }

  ReportMapState copyWith({
    MapArea? area,
    ReportStatus? Function()? filter,
    List<MapReport>? reports,
    bool? truncated,
    bool? loading,
    bool? loaded,
    ApiFailure? Function()? failure,
    String? Function()? selectedId,
    bool? confirming,
    String? Function()? confirmError,
    bool? confirmedNotice,
  }) => ReportMapState(
    area: area ?? this.area,
    filter: filter == null ? this.filter : filter(),
    reports: reports ?? this.reports,
    truncated: truncated ?? this.truncated,
    loading: loading ?? this.loading,
    loaded: loaded ?? this.loaded,
    failure: failure == null ? this.failure : failure(),
    selectedId: selectedId == null ? this.selectedId : selectedId(),
    confirming: confirming ?? this.confirming,
    confirmError: confirmError == null ? this.confirmError : confirmError(),
    confirmedNotice: confirmedNotice ?? this.confirmedNotice,
  );
}

/// Mapa de reportes: pide los del área visible y permite confirmar uno ajeno (HU-16).
/// Depende del ciudadano en sesión (propuesta 56): al cerrar la sesión se vacía.
final reportMapProvider = NotifierProvider<ReportMapController, ReportMapState>(
  ReportMapController.new,
);

class ReportMapController extends Notifier<ReportMapState> {
  /// Número de la última consulta: una respuesta que llega tarde no pisa una más nueva.
  int _request = 0;

  @override
  ReportMapState build() {
    ref.watch(currentUserIdProvider);
    return const ReportMapState();
  }

  /// El mapa se movió o quedó listo: pide los reportes del área nueva. Con [force] vuelve a
  /// pedirlos aunque el área no haya cambiado.
  Future<void> showArea(MapArea area, {bool force = false}) async {
    if (!force && area == state.area && state.failure == null) return;
    state = state.copyWith(area: area);
    await _load();
  }

  Future<void> setFilter(ReportStatus? filter) async {
    if (filter == state.filter) return;
    state = state.copyWith(filter: () => filter, selectedId: () => null);
    await _load();
  }

  /// Vuelve a pedir el área actual (tras un error o al volver a la pestaña).
  Future<void> reload() => _load();

  void select(String? reportId) =>
      state = state.copyWith(selectedId: () => reportId, confirmError: () => null);

  void noticeShown() => state = state.copyWith(confirmedNotice: false);

  /// Confirma un reporte ajeno desde su ficha. No cambia U: es evidencia (guía 2.2).
  Future<void> confirm(MapReport report) async {
    if (state.confirming || !report.canConfirm) return;
    state = state.copyWith(confirming: true, confirmError: () => null);
    try {
      final total = await ref.read(newReportRepositoryProvider).confirm(report.id);
      if (!ref.mounted) return;
      _replace(report.confirmed(total), notice: true);
      // El reporte confirmado pasa a aparecer en «Mis reportes».
      ref.invalidate(myReportsProvider);
    } on ApiError catch (e) {
      if (!ref.mounted) return;
      if (e.code == 'CONFIRMATION_ALREADY_EXISTS') {
        // Ya estaba confirmado (p. ej. una respuesta perdida): se considera hecho.
        _replace(report.confirmed(report.confirmations), notice: false);
      } else {
        state = state.copyWith(confirming: false, confirmError: () => e.message);
      }
    } on ApiFailure catch (e) {
      if (ref.mounted) state = state.copyWith(confirming: false, confirmError: () => e.message);
    }
  }

  void _replace(MapReport updated, {required bool notice}) {
    state = state.copyWith(
      reports: [for (final report in state.reports) report.id == updated.id ? updated : report],
      confirming: false,
      confirmedNotice: notice,
    );
  }

  Future<void> _load() async {
    final area = state.area;
    if (area == null) return;
    final request = ++_request;
    state = state.copyWith(loading: true, failure: () => null);
    try {
      final page = await ref
          .read(reportMapRepositoryProvider)
          .listInArea(area, status: state.filter);
      if (!ref.mounted || request != _request) return;
      state = state.copyWith(
        reports: page.items,
        truncated: page.truncated,
        loading: false,
        loaded: true,
        // Si el reporte elegido ya no está en el área, se cierra su ficha.
        selectedId: () =>
            page.items.any((report) => report.id == state.selectedId) ? state.selectedId : null,
      );
    } on ApiFailure catch (failure) {
      if (!ref.mounted || request != _request) return;
      state = state.copyWith(loading: false, failure: () => failure);
    }
  }
}
