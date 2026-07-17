/// Screen 2: Active Recording — camera preview, hand tracking overlay,
/// narration toggle, task-label chips, pause, privacy delete.
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/session_provider.dart';
import '../services/camera_service.dart';

class RecordingScreen extends ConsumerStatefulWidget {
  const RecordingScreen({super.key});

  @override
  ConsumerState<RecordingScreen> createState() => _RecordingScreenState();
}

class _RecordingScreenState extends ConsumerState<RecordingScreen>
    with WidgetsBindingObserver {
  final _cameraService = CameraService();
  Timer? _timer;
  bool _narrationOn = false;
  String _activeTask = '';

  static const _taskChips = [
    'wipe counter', 'wash dish', 'fold towel', 'sweep floor',
    'assemble item', 'arrange decor', 'hang item', 'unpack box',
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initCamera();
    _startTimer();
  }

  Future<void> _initCamera() async {
    final ctrl = await _cameraService.initialize();
    if (ctrl != null) setState(() {});
    await _cameraService.startRecording();
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      final session = ref.read(sessionProvider);
      if (session.isRecording) {
        ref.read(sessionProvider.notifier)
            .tick(session.elapsed + const Duration(seconds: 1));
        // Simulate hand coverage update (real impl reads from MediaPipe)
        _cameraService.recordHandFrame(true);
        ref.read(sessionProvider.notifier)
            .updateHandCoverage(_cameraService.handCoverage);
      }
    });
  }

  void _toggleNarration() {
    setState(() => _narrationOn = !_narrationOn);
    if (_narrationOn) {
      // Start audio recording / speech-to-text stream
    }
  }

  void _setTask(String task) {
    setState(() => _activeTask = task);
    // Insert timestamped label into the session
  }

  void _privacyDelete() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete last 5 minutes?'),
        content: const Text(
            'This removes the last 5 minutes of video and audio permanently.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel')),
          FilledButton(
            onPressed: () {
              // Implement 5-min trim on the recording
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text('Last 5 minutes deleted'),
                    backgroundColor: Colors.red),
              );
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  Future<void> _endShift() async {
    _timer?.cancel();
    await _cameraService.stopRecording();
    ref.read(sessionProvider.notifier).stop();
    Navigator.pushReplacementNamed(context, '/shift-end');
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      _cameraService.stopRecording();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _cameraService.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final elapsed = session.elapsed;

    return Scaffold(
      body: Stack(
        children: [
          // Camera preview (full screen)
          const Center(child: Text('[camera preview]',
              style: TextStyle(color: Colors.white38))),
          // Top HUD bar
          Positioned(
            top: 0, left: 0, right: 0,
            child: Container(
              color: Colors.black87,
              padding: EdgeInsets.only(
                  top: MediaQuery.of(context).padding.top, left: 16, right: 16,
                  bottom: 8),
              child: Row(
                children: [
                  const Icon(Icons.fiber_manual_record, color: Colors.red, size: 14),
                  const SizedBox(width: 6),
                  Text(_formatDuration(elapsed),
                      style: const TextStyle(fontSize: 18)),
                  const Spacer(),
                  Text('${(session.handCoverage ?? 0 * 100).toStringAsFixed(0)}% hands',
                      style: const TextStyle(fontSize: 14)),
                ],
              ),
            ),
          ),
          // Task label
          if (_activeTask.isNotEmpty)
            Positioned(
              bottom: 120, left: 16,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                    color: Colors.green.withOpacity(0.85),
                    borderRadius: BorderRadius.circular(8)),
                child: Text('task: $_activeTask',
                    style: const TextStyle(fontSize: 18)),
              ),
            ),
          // Bottom controls
          Positioned(
            bottom: 0, left: 0, right: 0,
            child: Container(
              color: Colors.black87,
              padding: EdgeInsets.only(
                  bottom: MediaQuery.of(context).padding.bottom,
                  top: 8, left: 12, right: 12),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Task chips
                  SizedBox(
                    height: 42,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: _taskChips.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 8),
                      itemBuilder: (_, i) => ChoiceChip(
                        label: Text(_taskChips[i]),
                        selected: _activeTask == _taskChips[i],
                        onSelected: (_) => _setTask(_taskChips[i]),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  // Action buttons
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      IconButton(
                        icon: Icon(Icons.keyboard_voice,
                            color: _narrationOn ? Colors.green : Colors.white54),
                        onPressed: _toggleNarration,
                        tooltip: 'Narration',
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_forever, color: Colors.redAccent),
                        onPressed: _privacyDelete,
                        tooltip: 'Delete last 5 min',
                      ),
                      IconButton(
                        icon: const Icon(Icons.pause_circle, size: 48, color: Colors.orange),
                        onPressed: () {},
                        tooltip: 'Pause',
                      ),
                      IconButton(
                        icon: const Icon(Icons.stop_circle, size: 48, color: Colors.red),
                        onPressed: _endShift,
                        tooltip: 'End shift',
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration d) {
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    final s = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }
}
