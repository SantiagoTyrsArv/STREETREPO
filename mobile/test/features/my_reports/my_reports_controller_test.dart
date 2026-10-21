import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/core/domain/report_enums.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/application/session_controller.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/session.dart';
import 'package:street_repo/features/my_reports/application/my_reports_controller.dart';
import 'package:street_repo/features/my_reports/domain/my_report.dart';
import 'package:street_repo/features/report_new/application/report_draft_controller.dart';
import 'package:street_repo/features/report_new/application/submit_report_controller.dart';

import '../../support/fake_auth_repository.dart';
import '../../support/fake_device_services.dart';
import '../../support/fake_my_reports_repository.dart';
import '../../support/fake_new_report_repository.dart';
import '../../support/memory_token_store.dart';

void main() {
  late FakeMyReportsRepository repository;

  setUp(() => repository = FakeMyReportsRepository());

  Future<ProviderContainer> signedIn() async {
    final store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
    final c = ProviderContainer.test(
      overrides: [
        tokenStoreProvider.overrideWithValue(store),
        authRepositoryProvider.overrideWithValue(FakeAuthRepository(store)),
        myReportsRepositoryProvider.overrideWithValue(repository),
        newReportRepositoryProvider.overrideWithValue(FakeNewReportRepository()),
        locationServiceProvider.overrideWithValue(FakeLocationService()),
        photoServiceProvider.overrideWithValue(FakePhotoService()),
      ],
    );
    expect(await c.read(sessionControllerProvider.future), isA<SignedIn>());
    c.listen(myReportsProvider, (_, _) {});
    return c;
  }

  List<MyReport> many(int count) => [for (var i = 0; i < count; i++) ownReport(id: 'r$i')];

  test('carga la primera página y pide la siguiente con offset 20', () async {
    repository.reports = many(25);
    final c = await signedIn();

    final first = await c.read(myReportsProvider.future);
    expect(first.items, hasLength(20));
    expect(first.hasMore, isTrue);

    await c.read(myReportsProvider.notifier).loadMore();

    expect(repository.pageOffsets, [0, 20]);
    expect(c.read(myReportsProvider).value!.items, hasLength(25));
    expect(c.read(myReportsProvider).value!.hasMore, isFalse);
  });

  test('sin más páginas no vuelve a pedir', () async {
    repository.reports = many(2);
    final c = await signedIn();
    await c.read(myReportsProvider.future);

    await c.read(myReportsProvider.notifier).loadMore();

    expect(repository.pageOffsets, [0]);
  });

  test('si falla la página siguiente conserva lo cargado', () async {
    repository.reports = many(25);
    final c = await signedIn();
    await c.read(myReportsProvider.future);
    repository.beforePage = () async => throw const NetworkFailure();

    await c.read(myReportsProvider.notifier).loadMore();

    final state = c.read(myReportsProvider).value!;
    expect(state.items, hasLength(20));
    expect(state.loadMoreFailure, isA<NetworkFailure>());
  });

  test('el filtro «Reparados» deja solo los reparados', () {
    final reports = [
      ownReport(id: 'a', status: ReportStatus.repaired),
      ownReport(id: 'b'),
      confirmedReport(status: ReportStatus.repaired),
    ];

    expect(reports.where(MyReportsFilter.repaired.accepts).map((r) => r.id), ['a', 'conf-1']);
    expect(reports.where(MyReportsFilter.inProgress.accepts).map((r) => r.id), ['b']);
  });

  test('enviar un reporte recarga la lista', () async {
    final c = await signedIn();
    await c.read(myReportsProvider.future);
    final draft = c.read(reportDraftProvider.notifier);
    await draft.capturePhoto();
    await draft.locate();
    draft.setSeverity(Severity.low);

    await c.read(submitReportProvider.notifier).submit();
    await c.read(myReportsProvider.future);

    expect(repository.pageOffsets, [0, 0]);
  });

  test('al cerrar sesión se vacía sin pedir nada (propuesta 56)', () async {
    repository.reports = many(3);
    final c = await signedIn();
    await c.read(myReportsProvider.future);

    await c.read(sessionControllerProvider.notifier).signOut();

    expect((await c.read(myReportsProvider.future)).items, isEmpty);
    expect(repository.pageOffsets, [0]);
  });
}
