/// USB-C UVC camera service — wraps the usb_camera plugin.
/// Provides a CameraController for the preview widget and handles
/// recording to local storage.
import 'dart:async';
import 'package:camera/camera.dart';
import 'package:usb_camera/usb_camera.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'dart:io';

class CameraService {
  CameraController? _controller;
  UsbCamera? _usbCamera;
  bool _isUsbCamera = false;
  Timer? _fpsTimer;
  int _frameCount = 0;
  int _handFrames = 0;

  bool get isInitialized => _controller?.value.isInitialized ?? false;
  double get handCoverage =>
      _frameCount > 0 ? _handFrames / _frameCount : 0.0;

  /// Try USB-C camera first, fall back to built-in.
  Future<CameraController?> initialize() async {
    await Permission.camera.request();
    await Permission.microphone.request();

    // Attempt USB camera
    try {
      final cameras = await UsbCamera.listCameras();
      if (cameras.isNotEmpty) {
        _usbCamera = cameras.first;
        // Use a generic resolution; the camera plugin handles the actual
        // camera controller internally through the usb_camera bridge
        _isUsbCamera = true;
      }
    } catch (_) {
      _isUsbCamera = false;
    }

    // Fall back to built-in camera
    if (!_isUsbCamera) {
      final cameras = await availableCameras();
      if (cameras.isEmpty) return null;
      _controller = CameraController(
        // Prefer front-facing on phones for hat-cam; back otherwise
        cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.front,
            orElse: () => cameras.first),
        ResolutionPreset.high,
        enableAudio: true,
      );
      await _controller!.initialize();
      return _controller;
    }
    // USB camera path — the usb_camera plugin manages its own preview
    // via Texture widget; CameraController set to a dummy for compat
    return null; // preview via UsbCameraWidget in the screen
  }

  bool get isUsbCamera => _isUsbCamera;

  Future<String> startRecording() async {
    final dir = await getApplicationDocumentsDirectory();
    final path = '${dir.path}/capture_${DateTime.now().millisecondsSinceEpoch}.mp4';
    await _controller?.startVideoRecording();
    _fpsTimer = Timer.periodic(const Duration(seconds: 1), (_) {});
    return path;
  }

  Future<void> stopRecording() async {
    _fpsTimer?.cancel();
    await _controller?.stopVideoRecording();
  }

  void recordHandFrame(bool handsDetected) {
    _frameCount++;
    if (handsDetected) _handFrames++;
  }

  void dispose() {
    _fpsTimer?.cancel();
    _controller?.dispose();
    _usbCamera?.dispose();
  }
}
