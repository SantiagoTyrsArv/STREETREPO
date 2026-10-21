import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/domain/report_enums.dart';
import '../../../core/network/api_error.dart';
import '../../auth/application/auth_providers.dart';
import '../../auth/application/session_controller.dart';
import '../../report_new/application/submit_report_controller.dart';
import '../../report_new/domain/submit_outcome.dart';
import '../data/http_my_reports_repository.dart';
import '../domain/my_report.dart';
import '../domain/my_reports_repository.dart';
import '../domain/report_detail.dart';

final myReportsRepositoryProvider = Provider<MyReportsRepository>(
  (ref) => HttpMyReportsRepository(ref.watch(apiClientProvider)),
);

/// Filtros de «Mis reportes», aplicados sobre lo ya cargado.
enum MyReportsFilter {
  all('Todos'),
  inProgress('En proceso'),
  repaired('Reparados');

  const MyReportsFilter(this.label);

  final String label;

  bool accepts(MyReport report) => switch (this) {
    MyReportsFilter.all => true,
    MyReportsFilter.inProgress => report.status != ReportStatus.repaired,
    MyReportsFilter.repaired => report.status == ReportStatus.repaired,
  };
}

class MyReportsState {
  const MyReportsState({
    required this.items,
    required this.total,
    this.loadingMore = false,
    this.loadMoreFailure,
  });

  static const empty = MyReportsState(items: [], total: 0);

  final List<MyReport> items;
  final int total;
  final bool loadingMore;

  /// Falló la carga de la página siguiente; lo ya cargado se conserva.
  final ApiFailure? loadMoreFailure;

  bool get hasMore => items.length < total;

  MyReportsState copyWith({
    List<MyReport>? items,
    int? total,
    bool? loadingMore,
    ApiFailure? loadMoreFailure,
  }) => MyReportsState(
    items: items ?? this.items,
    total: total ?? this.total,
    loadingMore: loadingMore ?? this.loadingMore,
    loadMoreFailure: loadMoreFailure,
  );
}

/// «Mis reportes»: reportes creados y confirmados, por páginas. Depende del ciudadano en
/// sesión (propuesta 56) y se recarga tras enviar o confirmar un reporte.
final myReportsProvider = AsyncNotifierProvider<MyReportsController, MyReportsState>(
  MyReportsController.new,
  // Sin red, la pantalla ofrece «Reintentar»; no se reintenta a ciegas.
  retry: (_, _) => null,
);

class MyReportsController extends AsyncNotifier<MyReportsState> {
  MyReportsRepository get _repository => ref.read(myReportsRepositoryProvider);

  @override
  Future<MyReportsState> build() {
    if (ref.watch(currentUserIdProvider) == null) return Future.value(MyReportsState.empty);
    ref.listen(submitReportProvider.select((s) => s.outcome), (_, outcome) {
      if (outcome is Sent || outcome is Confirmed) ref.invalidateSelf();
    });
    return _firstPage();
  }

  Future<MyReportsState> _firstPage() async {
    final page = await _repository.page(offset: 0);
    return MyReportsState(items: page.items, total: page.total);
  }

  /// Vuelve a cargar desde el principio (deslizar hacia abajo). Si falla con una lista ya
  /// cargada, la conserva y devuelve el fallo para avisarlo.
  Future<ApiFailure?> refresh() async {
    try {
      final fresh = await _firstPage();
      if (ref.mounted) state = AsyncData(fresh);
      return null;
    } on ApiFailure catch (failure) {
      if (ref.mounted && !state.hasValue) state = AsyncError(failure, StackTrace.current);
      return failure;
    }
  }

  /// Tras un error de la primera carga.
  Future<void> retry() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(_firstPage);
  }

  /// Pide la página siguiente al llegar al final de la lista.
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || current.loadingMore || !current.hasMore) return;
    state = AsyncData(current.copyWith(loadingMore: true));
    try {
      final page = await _repository.page(offset: current.items.length);
      if (!ref.mounted) return;
      // Si entró un reporte nuevo entre páginas, el primero de esta ya estaba en la lista.
      final seen = {for (final item in current.items) _key(item)};
      state = AsyncData(
        MyReportsState(
          items: [...current.items, ...page.items.where((item) => !seen.contains(_key(item)))],
          total: page.total,
        ),
      );
    } on ApiFailure catch (failure) {
      if (ref.mounted) state = AsyncData(current.copyWith(loadMoreFailure: failure));
    }
  }

  static String _key(MyReport report) => '${report.runtimeType}:${report.id}';
}

/// Detalle de un reporte. Sin sesión no se pide nada (el proveedor puede reconstruirse al
/// cerrar la sesión antes de que la pantalla desaparezca).
final reportDetailProvider = FutureProvider.autoDispose.family<ReportDetail, String>((ref, id) {
  if (ref.watch(currentUserIdProvider) == null) throw StateError('Sin sesión');
  return ref.read(myReportsRepositoryProvider).detail(id);
}, retry: (_, _) => null);

/// Miniatura de un reporte propio: solo en memoria y mientras se muestre (propuesta 54).
final reportThumbnailProvider = FutureProvider.autoDispose.family<Uint8List, String>((ref, id) {
  if (ref.watch(currentUserIdProvider) == null) throw StateError('Sin sesión');
  return ref.read(myReportsRepositoryProvider).thumbnail(id);
}, retry: (_, _) => null);

/// Foto de un reporte propio para el detalle: solo en memoria y mientras se muestre.
final reportPhotoProvider = FutureProvider.autoDispose.family<Uint8List, String>((ref, id) {
  if (ref.watch(currentUserIdProvider) == null) throw StateError('Sin sesión');
  return ref.read(myReportsRepositoryProvider).photo(id);
}, retry: (_, _) => null);
