import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Configuración de la app. La URL del backend llega solo por
/// `--dart-define=API_BASE_URL=...`: no hay un valor por defecto que pueda colarse en release.
/// El proveedor de teselas del mapa se puede cambiar con `--dart-define=MAP_TILE_URL=...`
/// (guía 3.1); por defecto, las públicas de OpenStreetMap.
class AppConfig {
  const AppConfig._(this.apiBaseUrl, this.tileUrlTemplate);

  factory AppConfig.fromEnvironment() => AppConfig.parse(
    const String.fromEnvironment('API_BASE_URL'),
    tileUrl: const String.fromEnvironment('MAP_TILE_URL'),
  );

  factory AppConfig.parse(String raw, {String tileUrl = ''}) {
    final uri = Uri.tryParse(raw.trim());
    if (raw.trim().isEmpty) {
      throw StateError('Falta --dart-define=API_BASE_URL');
    }
    if (uri == null || !(uri.isScheme('http') || uri.isScheme('https')) || uri.host.isEmpty) {
      throw StateError('API_BASE_URL debe ser una URL http(s): $raw');
    }
    final tiles = tileUrl.trim().isEmpty ? defaultTileUrl : tileUrl.trim();
    if (!tiles.startsWith('https://') || !tiles.contains('{z}')) {
      throw StateError('MAP_TILE_URL debe ser una plantilla https con {z}/{x}/{y}: $tiles');
    }
    return AppConfig._(uri, tiles);
  }

  static const String apiPrefix = '/api/v1';

  static const String defaultTileUrl = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

  final Uri apiBaseUrl;

  /// Plantilla `{z}/{x}/{y}` de las teselas del mapa.
  final String tileUrlTemplate;

  Uri apiUrl(String path) => apiBaseUrl.replace(path: '$apiPrefix$path');
}

final appConfigProvider = Provider<AppConfig>((ref) => AppConfig.fromEnvironment());
