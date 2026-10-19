import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Configuración de la app. La URL del backend llega solo por
/// `--dart-define=API_BASE_URL=...`: no hay un valor por defecto que pueda colarse en release.
class AppConfig {
  const AppConfig._(this.apiBaseUrl);

  factory AppConfig.fromEnvironment() =>
      AppConfig.parse(const String.fromEnvironment('API_BASE_URL'));

  factory AppConfig.parse(String raw) {
    final uri = Uri.tryParse(raw.trim());
    if (raw.trim().isEmpty) {
      throw StateError('Falta --dart-define=API_BASE_URL');
    }
    if (uri == null || !(uri.isScheme('http') || uri.isScheme('https')) || uri.host.isEmpty) {
      throw StateError('API_BASE_URL debe ser una URL http(s): $raw');
    }
    return AppConfig._(uri);
  }

  static const String apiPrefix = '/api/v1';

  final Uri apiBaseUrl;

  Uri apiUrl(String path) => apiBaseUrl.replace(path: '$apiPrefix$path');
}

final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.fromEnvironment());
