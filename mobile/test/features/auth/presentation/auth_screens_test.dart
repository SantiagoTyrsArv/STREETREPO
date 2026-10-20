import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:street_repo/app.dart';
import 'package:street_repo/core/network/api_error.dart';
import 'package:street_repo/core/platform/url_opener.dart';
import 'package:street_repo/features/auth/application/auth_providers.dart';
import 'package:street_repo/features/auth/data/token_store.dart';
import 'package:street_repo/features/auth/domain/session.dart';

import '../../../support/fake_auth_repository.dart';
import '../../../support/load_fonts.dart';
import '../../../support/memory_token_store.dart';

const _password = 'una-clave-larga';

void main() {
  late MemoryTokenStore store;
  late FakeAuthRepository auth;
  late List<Uri> openedUrls;

  setUpAll(loadAppFonts);

  setUp(() {
    store = MemoryTokenStore();
    auth = FakeAuthRepository(store);
    openedUrls = [];
  });

  /// La app completa en un celular de 390×844 (el marco del Figma).
  Future<void> pumpApp(WidgetTester tester, {double textScale = 1}) async {
    tester.view
      ..physicalSize = const Size(390 * 3, 844 * 3)
      ..devicePixelRatio = 3;
    tester.platformDispatcher.textScaleFactorTestValue = textScale;
    addTearDown(tester.view.reset);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          tokenStoreProvider.overrideWithValue(store),
          authRepositoryProvider.overrideWithValue(auth),
          urlOpenerProvider.overrideWithValue((url) async {
            openedUrls.add(url);
            return true;
          }),
        ],
        child: const StreetRepoApp(),
      ),
    );
    await tester.pumpAndSettle();
    final scaler = MediaQuery.of(tester.element(find.byType(Scaffold).first)).textScaler;
    expect(scaler.scale(10), 10 * textScale, reason: 'la escala de texto llega a la app');
  }

  Finder field(String label) =>
      find.descendant(of: find.bySemanticsLabel(label), matching: find.byType(TextField));

  FilledButton button(WidgetTester tester, String label) =>
      tester.widget<FilledButton>(find.widgetWithText(FilledButton, label));

  Future<void> openRegister(WidgetTester tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('Crear cuenta'));
    await tester.pumpAndSettle();
  }

  Future<void> fillRegister(WidgetTester tester) async {
    await tester.enterText(field('Nombre'), 'Ana Ortega');
    await tester.enterText(field('Correo electrónico'), 'ana@correo.co');
    await tester.enterText(field('Contraseña'), _password);
  }

  /// Desplaza la pantalla visible (la última ruta) hasta que aparezca [text].
  Future<void> scrollTo(WidgetTester tester, String text) => tester.scrollUntilVisible(
    find.text(text),
    200,
    scrollable: find
        .descendant(of: find.byType(SingleChildScrollView).last, matching: find.byType(Scrollable))
        .first,
  );

  Future<void> tapCheckbox(WidgetTester tester, String labelStart) async {
    await tester.tap(find.bySemanticsLabel(RegExp('^${RegExp.escape(labelStart)}')));
    await tester.pumpAndSettle();
  }

  group('Bienvenida', () {
    testWidgets('sin sesión abre en la Bienvenida y lleva a las dos opciones', (tester) async {
      await pumpApp(tester);

      expect(find.text('Street Repo'), findsOneWidget);
      await tester.tap(find.text('Ya tengo cuenta'));
      await tester.pumpAndSettle();
      expect(find.text('Bienvenida de nuevo'), findsOneWidget);

      await tester.tap(find.bySemanticsLabel('Volver'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Crear cuenta'));
      await tester.pumpAndSettle();
      expect(find.text('Crea tu cuenta'), findsOneWidget);
    });

    testWidgets('con sesión guardada abre directamente en «Mis reportes»', (tester) async {
      store = MemoryTokenStore(const AuthTokens(access: 'a', refresh: 'r'));
      auth = FakeAuthRepository(store);

      await pumpApp(tester);

      expect(find.text('Street Repo'), findsNothing);
      expect(find.byType(Placeholder), findsOneWidget);
    });
  });

  group('Registro', () {
    testWidgets('muestra la versión vigente y no deja registrarse sin aceptarla', (tester) async {
      await openRegister(tester);
      await fillRegister(tester);

      expect(find.textContaining('(versión 1.0)'), findsOneWidget);
      expect(button(tester, 'Crear cuenta').onPressed, isNull);

      await tapCheckbox(tester, 'Acepto la política');

      expect(button(tester, 'Crear cuenta').onPressed, isNotNull);
    });

    testWidgets('un registro correcto entra a «Mis reportes»', (tester) async {
      await openRegister(tester);
      await fillRegister(tester);
      await tapCheckbox(tester, 'Acepto la política');

      await tester.tap(find.text('Crear cuenta'));
      await tester.pumpAndSettle();

      expect(auth.registeredPolicyVersion, '1.0');
      expect(auth.loggedInEmail, 'ana@correo.co');
      expect(find.byType(Placeholder), findsOneWidget);
    });

    testWidgets('un correo repetido se muestra bajo el campo y conserva lo escrito', (
      tester,
    ) async {
      auth.registerFailure = const ApiError(
        status: 409,
        code: 'EMAIL_ALREADY_REGISTERED',
        message: 'Ya existe una cuenta con ese correo.',
      );
      await openRegister(tester);
      await fillRegister(tester);
      await tapCheckbox(tester, 'Acepto la política');

      await tester.tap(find.text('Crear cuenta'));
      await tester.pumpAndSettle();

      expect(find.text('Ya existe una cuenta con ese correo.'), findsOneWidget);
      expect(find.text('Ana Ortega'), findsOneWidget);
      expect(find.text('ana@correo.co'), findsOneWidget);
      expect(tester.widget<TextField>(field('Contraseña')).controller!.text, _password);
    });

    testWidgets('si se creó la cuenta pero no pudo entrar, lleva a «Ingresar» con el correo', (
      tester,
    ) async {
      auth.loginFailure = const NetworkFailure();
      await openRegister(tester);
      await fillRegister(tester);
      await tapCheckbox(tester, 'Acepto la política');

      await tester.tap(find.text('Crear cuenta'));
      await tester.pumpAndSettle();

      expect(find.text('Bienvenida de nuevo'), findsOneWidget);
      expect(find.textContaining('Tu cuenta quedó creada'), findsOneWidget);
      expect(
        tester.widget<TextField>(field('Correo electrónico')).controller!.text,
        'ana@correo.co',
      );
    });

    testWidgets('sin poder cargar la política, ofrece reintentar', (tester) async {
      auth.onPrivacyPolicy = () async => throw const NetworkFailure();
      await openRegister(tester);

      expect(find.textContaining('No pudimos cargar la política'), findsOneWidget);
      expect(button(tester, 'Crear cuenta').onPressed, isNull);

      auth.onPrivacyPolicy = () async => const PrivacyPolicy(version: '1.0');
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();

      expect(find.textContaining('(versión 1.0)'), findsOneWidget);
    });
  });

  group('Política de datos', () {
    testWidgets('aceptarla vuelve al registro con la casilla marcada y lo escrito', (tester) async {
      auth.onPrivacyPolicy = () async =>
          PrivacyPolicy(version: '1.0', url: Uri.parse('https://streetrepo.co/politica'));
      await openRegister(tester);
      await fillRegister(tester);

      await tester.tap(find.text('Leer la política'));
      await tester.pumpAndSettle();
      expect(find.text('Tu información, con tu permiso'), findsOneWidget);
      expect(find.text('Versión 1.0 de la política.'), findsOneWidget);
      expect(button(tester, 'Aceptar y continuar').onPressed, isNull);

      await tester.ensureVisible(find.text('Leer la política completa'));
      await tester.tap(find.text('Leer la política completa'));
      expect(openedUrls, [Uri.parse('https://streetrepo.co/politica')]);

      await tapCheckbox(tester, 'He leído y acepto');
      await tester.tap(find.text('Aceptar y continuar'));
      await tester.pumpAndSettle();

      expect(find.text('Crea tu cuenta'), findsOneWidget);
      expect(find.text('Ana Ortega'), findsOneWidget);
      expect(button(tester, 'Crear cuenta').onPressed, isNotNull);
    });

    testWidgets('sin texto publicado lo dice en lugar del enlace', (tester) async {
      await openRegister(tester);
      await tester.tap(find.text('Leer la política'));
      await tester.pumpAndSettle();

      expect(find.text('El texto completo aún no está publicado.'), findsOneWidget);
      expect(find.text('Leer la política completa'), findsNothing);
    });
  });

  group('Iniciar sesión', () {
    Future<void> openLogin(WidgetTester tester) async {
      await pumpApp(tester);
      await tester.tap(find.text('Ya tengo cuenta'));
      await tester.pumpAndSettle();
      await tester.enterText(field('Correo electrónico'), 'ana@correo.co');
      await tester.enterText(field('Contraseña'), 'mala');
    }

    testWidgets('credenciales incorrectas muestran el aviso', (tester) async {
      auth.loginFailure = const ApiError(
        status: 401,
        code: 'INVALID_CREDENTIALS',
        message: 'Correo o contraseña incorrectos.',
      );
      await openLogin(tester);

      await tester.tap(find.text('Entrar'));
      await tester.pumpAndSettle();

      expect(find.text('Correo o contraseña incorrectos.'), findsOneWidget);
      expect(find.text('ana@correo.co'), findsOneWidget);
    });

    testWidgets('demasiados intentos bloquean con cuenta regresiva', (tester) async {
      auth.loginFailure = const ApiError(
        status: 429,
        code: 'TOO_MANY_LOGIN_ATTEMPTS',
        message: 'Demasiados intentos fallidos.',
        retryAfter: Duration(seconds: 90),
      );
      await openLogin(tester);

      await tester.tap(find.text('Entrar'));
      await tester.pump();

      expect(find.text('Demasiados intentos fallidos'), findsOneWidget);
      expect(find.textContaining('espera 1 min 30 s'), findsOneWidget);
      expect(button(tester, 'Reintentar en 1:30').onPressed, isNull);

      await tester.pump(const Duration(seconds: 1));
      expect(find.text('Reintentar en 1:29'), findsOneWidget);

      await tester.pump(const Duration(seconds: 89));
      expect(button(tester, 'Entrar').onPressed, isNotNull);
    });

    testWidgets('un ingreso correcto entra a «Mis reportes»', (tester) async {
      await openLogin(tester);

      await tester.tap(find.text('Entrar'));
      await tester.pumpAndSettle();

      expect(find.byType(Placeholder), findsOneWidget);
    });
  });

  group('Texto del sistema al doble (Review Focus 4)', () {
    // Un desbordamiento (RenderFlex overflow) hace fallar la prueba por sí solo.
    testWidgets('Bienvenida', (tester) async {
      await pumpApp(tester, textScale: 2);
      await scrollTo(tester, 'Ya tengo cuenta');
      expect(find.text('Ya tengo cuenta'), findsOneWidget);
    });

    testWidgets('Registro y Política', (tester) async {
      await pumpApp(tester, textScale: 2);
      await scrollTo(tester, 'Crear cuenta');
      await tester.tap(find.text('Crear cuenta'));
      await tester.pumpAndSettle();
      await scrollTo(tester, 'Leer la política');
      await tester.tap(find.text('Leer la política'));
      await tester.pumpAndSettle();
      await scrollTo(tester, 'Aceptar y continuar');
      expect(find.text('Aceptar y continuar'), findsOneWidget);
    });

    testWidgets('Iniciar sesión bloqueada', (tester) async {
      auth.loginFailure = const ApiError(
        status: 429,
        code: 'TOO_MANY_LOGIN_ATTEMPTS',
        message: 'Demasiados intentos fallidos.',
        retryAfter: Duration(minutes: 4, seconds: 32),
      );
      await pumpApp(tester, textScale: 2);
      await scrollTo(tester, 'Ya tengo cuenta');
      await tester.tap(find.text('Ya tengo cuenta'));
      await tester.pumpAndSettle();
      await scrollTo(tester, 'Entrar');
      await tester.tap(find.text('Entrar'));
      await tester.pump();
      await scrollTo(tester, 'Reintentar en 4:32');
      expect(find.text('Reintentar en 4:32'), findsOneWidget);
    });
  });
}
