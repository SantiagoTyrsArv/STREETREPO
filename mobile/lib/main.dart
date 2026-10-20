import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'app.dart';
import 'core/config/app_config.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Falla al arrancar si falta --dart-define=API_BASE_URL, con ese mensaje, en lugar de
  // aparecer después como un error de red confuso.
  final config = AppConfig.fromEnvironment();
  await initializeDateFormatting('es_CO');
  runApp(
    ProviderScope(
      overrides: [appConfigProvider.overrideWithValue(config)],
      child: const StreetRepoApp(),
    ),
  );
}
