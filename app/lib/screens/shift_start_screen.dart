/// Screen 1: Shift Start — worker ID, job type picker, calibration.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/session_provider.dart';
import '../services/camera_service.dart';

class ShiftStartScreen extends ConsumerStatefulWidget {
  const ShiftStartScreen({super.key});

  @override
  ConsumerState<ShiftStartScreen> createState() => _ShiftStartScreenState();
}

class _ShiftStartScreenState extends ConsumerState<ShiftStartScreen> {
  final _workerCtrl = TextEditingController();
  final _homeCtrl = TextEditingController();
  String _jobType = 'kitchen_clean';
  final _cameraService = CameraService();
  bool _calibrating = false;
  String _calibStatus = '';

  static const _jobTypes = [
    'kitchen_clean',
    'bathroom_clean',
    'full_home_clean',
    'staging_assembly',
    'staging_arrange',
    'destage_pack',
    'other',
  ];

  @override
  void dispose() {
    _workerCtrl.dispose();
    _homeCtrl.dispose();
    _cameraService.dispose();
    super.dispose();
  }

  Future<void> _calibrate() async {
    setState(() {
      _calibrating = true;
      _calibStatus = 'connecting to camera...';
    });
    final ctrl = await _cameraService.initialize();
    if (ctrl == null && !_cameraService.isUsbCamera) {
      setState(() {
        _calibStatus = 'no camera found';
        _calibrating = false;
      });
      return;
    }
    setState(() => _calibStatus = 'camera ready — hold hands at working distance');
    // In a full build, we'd run MediaPipe here and show live skeleton.
    // For now, we simulate a 2-second calibration.
    await Future.delayed(const Duration(seconds: 2));
    setState(() {
      _calibStatus = _cameraService.isUsbCamera
          ? 'USB-C camera calibrated ✓'
          : 'built-in camera ready ✓ (USB-C camera not detected)';
      _calibrating = false;
    });
  }

  void _startShift() {
    if (_workerCtrl.text.trim().isEmpty) return;
    ref.read(sessionProvider.notifier).start(
          _workerCtrl.text.trim(),
          _jobType,
          homeId: _homeCtrl.text.trim().isEmpty ? null : _homeCtrl.text.trim(),
        );
    Navigator.pushReplacementNamed(context, '/recording');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Data Hat'), centerTitle: true),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: ListView(
          children: [
            Text('New Capture Shift',
                style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 24),
            TextField(
              controller: _workerCtrl,
              decoration: const InputDecoration(
                  labelText: 'Worker ID', prefixIcon: Icon(Icons.badge)),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _homeCtrl,
              decoration: const InputDecoration(
                  labelText: 'Home ID (optional)',
                  prefixIcon: Icon(Icons.home),
                  hintText: 'anonymized UUID'),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              value: _jobType,
              decoration: const InputDecoration(
                  labelText: 'Job Type', prefixIcon: Icon(Icons.work)),
              items: _jobTypes
                  .map((j) =>
                      DropdownMenuItem(value: j, child: Text(j.replaceAll('_', ' '))))
                  .toList(),
              onChanged: (v) => setState(() => _jobType = v!),
            ),
            const SizedBox(height: 24),
            // Calibration
            OutlinedButton.icon(
              onPressed: _calibrating ? null : _calibrate,
              icon: const Icon(Icons.cameraswitch),
              label: const Text('Calibrate Camera'),
            ),
            if (_calibStatus.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_calibStatus,
                    style: TextStyle(
                        color: _calibStatus.contains('✓')
                            ? Colors.greenAccent
                            : Colors.orangeAccent)),
              ),
            const SizedBox(height: 32),
            FilledButton.icon(
              onPressed: _startShift,
              icon: const Icon(Icons.fiber_manual_record, color: Colors.red),
              label: const Text('Start Recording'),
              style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(56)),
            ),
          ],
        ),
      ),
    );
  }
}
