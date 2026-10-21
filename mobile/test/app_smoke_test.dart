import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/app.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/presentation/welcome_screen.dart';
import 'package:street_repo/features/my_reports/application/my_reports_controller.dart';
import 'package:street_repo/features/my_reports/presentation/my_reports_screen.dart';

import 'support/fake_auth_repository.dart';
import 'support/fake_my_reports_repository.dart';
import 'support/load_fonts.dart';
import 'support/memory_token_store.dart';

/// Arranque de la app completa (router real, redirección por sesión) con repositorios falsos.
void main() {
  setUpAll(loadAppFonts);

  Future<FakeAuthRepository> pumpApp(WidgetTester tester, {AuthTokens? saved}) async {
    final auth = FakeAuthRepository(MemoryTokenStore(saved));
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStoreProvider.overrideWithValue(auth.store),
          authRepositoryProvider.overrideWithValue(auth),
          myReportsRepositoryProvider.overrideWithValue(FakeMyReportsRepository()),
        ],
        child: const StreetRepoApp(),
      ),
    );
    await tester.pumpAndSettle();
    return auth;
  }

  testWidgets('sin sesión guardada arranca en la Bienvenida', (tester) async {
    final auth = await pumpApp(tester);

    expect(find.byType(WelcomeScreen), findsOneWidget);
    expect(auth.calls, isNot(contains('me')));
  });

  testWidgets('con sesión guardada arranca en «Mis reportes»', (tester) async {
    final auth = await pumpApp(
      tester,
      saved: const AuthTokens(access: 'a', refresh: 'r'),
    );

    expect(find.byType(MyReportsScreen), findsOneWidget);
    expect(auth.calls, contains('me'));
  });
}
