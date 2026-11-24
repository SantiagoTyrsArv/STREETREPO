import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:street_repo/app.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/core/platform/url_opener.dart';
import 'package:street_repo/core/routing/app_router.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/my_reports/application/my_reports_controller.dart';

import '../../../support/accessibility.dart';
import '../../../support/fake_auth_repository.dart';
import '../../../support/fake_my_reports_repository.dart';
import '../../../support/load_fonts.dart';
import '../../../support/memory_token_store.dart';

const _wrongPassword = ApiError(
  status: 403,
  code: 'PASSWORD_CONFIRMATION_FAILED',
  message: 'La contraseña actual no es correcta.',
);

void main() {
  late FakeAuthRepository auth;

  setUpAll(loadAppFonts);

  setUp(() {
    auth = FakeAuthRepository(MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r')));
  });

  /// La app con un ciudadano en sesión, ya en la pestaña Perfil.
  Future<void> pumpProfile(WidgetTester tester, {double textScale = 1}) async {
    tester.view
      ..physicalSize = const Size(390 * 3, 844 * 3)
      ..devicePixelRatio = 3;
    tester.platformDispatcher.textScaleFactorTestValue = textScale;
    addTearDown(tester.view.reset);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStoreProvider.overrideWithValue(auth.store),
          authRepositoryProvider.overrideWithValue(auth),
          urlOpenerProvider.overrideWithValue((_) async => true),
          myReportsRepositoryProvider.overrideWithValue(FakeMyReportsRepository()),
        ],
        child: const StreetRepoApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel('Perfil'));
    await tester.pumpAndSettle();
  }

  Future<void> tapVisible(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  Finder field(String label) =>
      find.descendant(of: find.bySemanticsLabel(label), matching: find.byType(TextField));

  Finder button(String label) => find.widgetWithText(FilledButton, label);

  String location(WidgetTester tester) =>
      GoRouter.of(tester.element(find.byType(Scaffold).last)).state.matchedLocation;

  group('Editar datos', () {
    Future<void> openEdit(WidgetTester tester) async {
      await pumpProfile(tester);
      await tapVisible(tester, find.text('Conocer y actualizar mis datos'));
    }

    testWidgets('muestra los datos guardados del titular', (tester) async {
      await openEdit(tester);

      expect(find.text('Editar datos'), findsOneWidget);
      expect(tester.widget<TextField>(field('Nombre')).controller!.text, 'Ana');
      expect(
        tester.widget<TextField>(field('Correo electrónico')).controller!.text,
        'ana@correo.co',
      );
      expect(find.text('Cambiar el correo requiere tu contraseña'), findsOneWidget);
    });

    testWidgets('cambiar el nombre guarda sin pedir contraseña y vuelve al Perfil', (tester) async {
      await openEdit(tester);
      await tester.enterText(field('Nombre'), 'Ana María');

      await tapVisible(tester, button('Guardar cambios'));

      expect(auth.updated, (name: 'Ana María', email: null, currentPassword: null));
      expect(find.text('Confirma tu contraseña'), findsNothing);
      expect(location(tester), AppRoutes.profile);
      expect(find.text('Ana María'), findsOneWidget);
      expect(find.text('Tus datos quedaron actualizados.'), findsOneWidget);
    });

    testWidgets('cambiar el correo pide la contraseña antes de guardar', (tester) async {
      await openEdit(tester);
      await tester.enterText(field('Correo electrónico'), 'nueva@correo.co');
      await tapVisible(tester, button('Guardar cambios'));

      expect(find.text('Confirma tu contraseña'), findsOneWidget);
      expect(auth.calls, isNot(contains('updateProfile')));

      await tester.enterText(field('Contraseña actual'), 'una-clave-larga');
      await tapVisible(tester, button('Confirmar'));

      expect(auth.updated, (
        name: null,
        email: 'nueva@correo.co',
        currentPassword: 'una-clave-larga',
      ));
      expect(location(tester), AppRoutes.profile);
      expect(find.text('nueva@correo.co'), findsOneWidget);
    });

    testWidgets('la contraseña incorrecta se queda en la hoja y conserva lo escrito', (
      tester,
    ) async {
      auth.updateFailure = _wrongPassword;
      await openEdit(tester);
      await tester.enterText(field('Correo electrónico'), 'nueva@correo.co');
      await tapVisible(tester, button('Guardar cambios'));
      await tester.enterText(field('Contraseña actual'), 'mala');

      await tapVisible(tester, button('Confirmar'));

      expect(find.text('Confirma tu contraseña'), findsOneWidget);
      expect(find.text('La contraseña actual no es correcta.'), findsOneWidget);
      expect(
        tester.widget<TextField>(field('Correo electrónico')).controller!.text,
        'nueva@correo.co',
      );
    });

    testWidgets('un correo de otra cuenta cierra la hoja y marca el campo', (tester) async {
      auth.updateFailure = const ApiError(
        status: 409,
        code: 'EMAIL_ALREADY_REGISTERED',
        message: 'Ya existe una cuenta con ese correo.',
      );
      await openEdit(tester);
      await tester.enterText(field('Correo electrónico'), 'otra@correo.co');
      await tapVisible(tester, button('Guardar cambios'));
      await tester.enterText(field('Contraseña actual'), 'una-clave-larga');

      await tapVisible(tester, button('Confirmar'));

      expect(find.text('Confirma tu contraseña'), findsNothing);
      expect(find.text('Ya existe una cuenta con ese correo.'), findsOneWidget);
      expect(location(tester), AppRoutes.editProfile);
    });

    testWidgets('un correo inválido se marca sin abrir la hoja', (tester) async {
      await openEdit(tester);
      await tester.enterText(field('Correo electrónico'), 'no-es-correo');

      await tapVisible(tester, button('Guardar cambios'));

      expect(find.text('Escribe un correo válido.'), findsOneWidget);
      expect(find.text('Confirma tu contraseña'), findsNothing);
    });

    testWidgets('«Cancelar» vuelve al Perfil sin guardar', (tester) async {
      await openEdit(tester);
      await tester.enterText(field('Nombre'), 'Otro nombre');

      await tapVisible(tester, button('Cancelar'));

      expect(location(tester), AppRoutes.profile);
      expect(auth.calls, isNot(contains('updateProfile')));
    });
  });

  group('Eliminar mis datos', () {
    Future<void> openDelete(WidgetTester tester) async {
      await pumpProfile(tester);
      await tapVisible(tester, find.text('Solicitar supresión de mis datos'));
    }

    testWidgets('explica qué se elimina y qué se conserva', (tester) async {
      await openDelete(tester);

      expect(find.text('Qué se elimina'), findsOneWidget);
      expect(find.text('Qué se conserva'), findsOneWidget);
      expect(find.textContaining('no se puede deshacer'), findsOneWidget);
    });

    testWidgets('sin contraseña no elimina nada', (tester) async {
      await openDelete(tester);

      await tapVisible(tester, button('Eliminar mis datos'));

      expect(find.text('Escribe tu contraseña actual.'), findsOneWidget);
      expect(auth.calls, isNot(contains('requestDataDeletion')));
    });

    testWidgets('la contraseña incorrecta deja la cuenta como estaba', (tester) async {
      auth.deletionFailure = _wrongPassword;
      await openDelete(tester);
      await tester.enterText(field('Contraseña actual'), 'mala');

      await tapVisible(tester, button('Eliminar mis datos'));

      expect(find.text('La contraseña actual no es correcta.'), findsOneWidget);
      expect(location(tester), AppRoutes.deleteData);
      expect(await auth.store.read(), isNotNull);
    });

    testWidgets('con la contraseña muestra la constancia y termina en la Bienvenida', (
      tester,
    ) async {
      await openDelete(tester);
      await tester.enterText(field('Contraseña actual'), 'una-clave-larga');

      await tapVisible(tester, button('Eliminar mis datos'));

      expect(auth.deletionPassword, 'una-clave-larga');
      expect(location(tester), AppRoutes.dataDeleted);
      expect(find.text('Tus datos fueron eliminados'), findsOneWidget);
      expect(find.text('Atendida'), findsOneWidget);
      expect(find.text('19 oct 2026 · 9:30 a. m.'), findsNWidgets(2));
      expect(find.text('Todas cerradas'), findsOneWidget);
      expect(await auth.store.read(), isNull);
      // La cuenta ya no existe: no se llama a cerrar sesión en el servidor.
      expect(auth.calls, isNot(contains('logout')));

      await tapVisible(tester, button('Finalizar'));

      expect(location(tester), AppRoutes.welcome);
    });

    testWidgets('«Cancelar» vuelve al Perfil sin eliminar', (tester) async {
      await openDelete(tester);

      await tapVisible(tester, button('Cancelar'));

      expect(location(tester), AppRoutes.profile);
      expect(auth.calls, isNot(contains('requestDataDeletion')));
    });
  });

  testWidgets('la constancia sin datos lleva a la Bienvenida', (tester) async {
    auth = FakeAuthRepository(MemoryTokenStore());
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStoreProvider.overrideWithValue(auth.store),
          authRepositoryProvider.overrideWithValue(auth),
        ],
        child: const StreetRepoApp(),
      ),
    );
    await tester.pumpAndSettle();

    GoRouter.of(tester.element(find.byType(Scaffold).first)).go(AppRoutes.dataDeleted);
    await tester.pumpAndSettle();

    expect(location(tester), AppRoutes.welcome);
  });

  group('Pautas de accesibilidad (fase 8)', () {
    testWidgets('Editar datos y hoja de contraseña', (tester) async {
      await pumpProfile(tester);
      await tapVisible(tester, find.text('Conocer y actualizar mis datos'));
      await expectMeetsAccessibilityGuidelines(tester);
      await tester.enterText(field('Correo electrónico'), 'nueva@correo.co');
      await tapVisible(tester, button('Guardar cambios'));
      expect(find.text('Confirma tu contraseña'), findsOneWidget);
      await expectMeetsAccessibilityGuidelines(tester);
    });

    testWidgets('Eliminar mis datos y constancia', (tester) async {
      await pumpProfile(tester);
      await tapVisible(tester, find.text('Solicitar supresión de mis datos'));
      await expectMeetsAccessibilityGuidelines(tester);
      await tester.enterText(field('Contraseña actual'), 'una-clave-larga');
      await tapVisible(tester, button('Eliminar mis datos'));
      expect(find.text('Tus datos fueron eliminados'), findsOneWidget);
      await expectMeetsAccessibilityGuidelines(tester);
    });
  });

  group('texto del sistema al doble', () {
    testWidgets('Editar datos, hoja de contraseña, Eliminar mis datos y Constancia', (
      tester,
    ) async {
      await pumpProfile(tester, textScale: 2);
      expect(tester.takeException(), isNull);

      await tapVisible(tester, find.text('Conocer y actualizar mis datos'));
      await tester.enterText(field('Correo electrónico'), 'nueva@correo.co');
      await tapVisible(tester, button('Guardar cambios'));
      expect(find.text('Confirma tu contraseña'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tapVisible(tester, button('Cancelar').last);
      await tapVisible(tester, button('Cancelar'));

      await tapVisible(tester, find.text('Solicitar supresión de mis datos'));
      expect(tester.takeException(), isNull);
      await tester.enterText(field('Contraseña actual'), 'una-clave-larga');
      await tapVisible(tester, button('Eliminar mis datos'));
      expect(find.text('Tus datos fueron eliminados'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
