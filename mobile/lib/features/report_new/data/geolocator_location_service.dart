import 'dart:async';

import 'package:geolocator/geolocator.dart';

import '../domain/device_services.dart';
import '../domain/report_draft.dart';

/// GPS con `geolocator`: escucha posiciones de alta precisión hasta tener una dentro de
/// [maxLocationAccuracyMeters] o agotar [timeLimit], y devuelve la mejor que haya visto.
class GeolocatorLocationService implements LocationService {
  const GeolocatorLocationService({this.timeLimit = const Duration(seconds: 15)});

  final Duration timeLimit;

  @override
  Future<LocationPermissionState> permission() async =>
      _withService(await Geolocator.checkPermission());

  @override
  Future<LocationPermissionState> request() async =>
      _withService(await Geolocator.requestPermission());

  Future<LocationPermissionState> _withService(LocationPermission permission) async {
    switch (permission) {
      case LocationPermission.denied:
      case LocationPermission.unableToDetermine:
        return LocationPermissionState.denied;
      case LocationPermission.deniedForever:
        return LocationPermissionState.deniedForever;
      case LocationPermission.whileInUse:
      case LocationPermission.always:
        return await Geolocator.isLocationServiceEnabled()
            ? LocationPermissionState.granted
            : LocationPermissionState.serviceDisabled;
    }
  }

  @override
  Future<GeoFix> currentFix() async {
    final positions = Geolocator.getPositionStream(
      locationSettings: AndroidSettings(intervalDuration: const Duration(seconds: 1)),
    );
    final best = Completer<Position?>();
    Position? bestSoFar;
    late final StreamSubscription<Position> subscription;
    final deadline = Timer(timeLimit, () {
      if (!best.isCompleted) best.complete(bestSoFar);
    });
    subscription = positions.listen(
      (position) {
        if (bestSoFar == null || position.accuracy < bestSoFar!.accuracy) bestSoFar = position;
        if (position.accuracy <= maxLocationAccuracyMeters && !best.isCompleted) {
          best.complete(position);
        }
      },
      onError: (Object _) {
        if (!best.isCompleted) best.complete(bestSoFar);
      },
    );
    final position = await best.future;
    deadline.cancel();
    await subscription.cancel();
    if (position == null) throw const LocationUnavailable();
    return GeoFix(
      latitude: position.latitude,
      longitude: position.longitude,
      accuracyMeters: position.accuracy,
    );
  }

  @override
  Future<void> openSettings(LocationPermissionState state) async {
    if (state == LocationPermissionState.serviceDisabled) {
      await Geolocator.openLocationSettings();
    } else {
      await Geolocator.openAppSettings();
    }
  }
}
