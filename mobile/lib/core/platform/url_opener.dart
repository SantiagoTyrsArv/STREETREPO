import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

typedef UrlOpener = Future<bool> Function(Uri url);

/// Abre un enlace en el navegador del sistema. Es un proveedor para probar sin abrirlo.
final urlOpenerProvider = Provider<UrlOpener>(
  (ref) =>
      (url) => launchUrl(url, mode: LaunchMode.externalApplication),
);
