import 'dart:io';

import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:image_picker/image_picker.dart';

import '../domain/device_services.dart';
import '../domain/report_draft.dart';

/// Cámara trasera con `image_picker` (la app de cámara del sistema: no hace falta declarar
/// el permiso CAMERA) y compresión con `flutter_image_compress`: JPEG de
/// [photoJpegQuality], girada según su orientación y **sin EXIF** (ubicación, dispositivo).
/// El servidor la vuelve a validar y recodificar (propuesta 35).
class PickerPhotoService implements PhotoService {
  PickerPhotoService([ImagePicker? picker]) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  /// Archivos de la cámara que no se pudieron borrar al tomar la foto.
  final Set<String> _leftovers = {};

  @override
  Future<CapturedPhoto?> takePhoto() async {
    final XFile? picked;
    try {
      picked = await _picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.rear,
      );
    } on Exception {
      throw const PhotoCaptureFailed();
    }
    if (picked == null) return null;
    try {
      final bytes = await FlutterImageCompress.compressWithFile(
        picked.path,
        minWidth: photoTargetShortSidePx,
        minHeight: photoTargetShortSidePx,
        quality: photoJpegQuality,
      );
      if (bytes == null || bytes.isEmpty) throw const PhotoCaptureFailed();
      return CapturedPhoto(bytes);
    } finally {
      // La foto original queda solo en memoria ya comprimida; el archivo temporal no se
      // conserva en el teléfono (propuesta 56).
      await _deleteQuietly(picked.path);
    }
  }

  /// Además de los archivos que no se pudieron borrar, en Android recoge la foto que la
  /// cámara entregó si el sistema cerró la app mientras estaba abierta, para borrarla.
  @override
  Future<void> discardTemporaryFiles() async {
    final paths = {..._leftovers};
    _leftovers.clear();
    if (Platform.isAndroid) {
      try {
        final lost = await _picker.retrieveLostData();
        paths.addAll((lost.files ?? const <XFile>[]).map((file) => file.path));
      } on Exception {
        // Sin datos perdidos que recuperar: no hay nada más que borrar.
      }
    }
    await Future.wait(paths.map(_deleteQuietly));
  }

  Future<void> _deleteQuietly(String path) async {
    try {
      await File(path).delete();
      _leftovers.remove(path);
    } on PathNotFoundException {
      _leftovers.remove(path);
    } on FileSystemException {
      // Se reintenta al cerrar la sesión; no impide el reporte.
      _leftovers.add(path);
    }
  }
}
