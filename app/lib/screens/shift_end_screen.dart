/// Screen 3: Shift End — summary stats, upload, worker rating.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/session_provider.dart';
import '../services/upload_service.dart';

class ShiftEndScreen extends ConsumerStatefulWidget {
  const ShiftEndScreen({super.key});

  @override
  ConsumerState<ShiftEndScreen> createState() => _ShiftEndScreenState();
}

class _ShiftEndScreenState extends ConsumerState<ShiftEndScreen> {
  bool _uploading = false;
  String _uploadStatus = '';
  int _rating = 0;

  Future<void> _upload() async {
    setState(() {
      _uploading = true;
      _uploadStatus = 'uploading...';
    });
    final session = ref.read(sessionProvider);
    final upload = UploadService(
        baseUrl: 'https://api.egodata.local', apiKey: null);
    try {
      final result = await upload.confirm(
        'raw/${session.workerId}/session.mp4',
        session.workerId,
        session.elapsed.inSeconds.toDouble(),
        handCoverage: session.handCoverage,
      );
      setState(() => _uploadStatus = 'uploaded — ${result['episode_id']}');
    } catch (e) {
      setState(() => _uploadStatus = 'upload failed: $e');
    }
    setState(() => _uploading = false);
  }

  @override
  Widget build(BuildContext context) {
    final session = ref.watch(sessionProvider);
    final cov = session.handCoverage ?? 0.0;

    return Scaffold(
      appBar: AppBar(title: const Text('Shift Complete'), centerTitle: true),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: ListView(
          children: [
            const Icon(Icons.check_circle, color: Colors.green, size: 80),
            const SizedBox(height: 16),
            Text('Shift finished',
                style: Theme.of(context).textTheme.headlineMedium,
                textAlign: TextAlign.center),
            const SizedBox(height: 32),
            _statRow('Worker', session.workerId),
            _statRow('Job type', session.jobType),
            _statRow('Duration',
                '${session.elapsed.inMinutes}m ${session.elapsed.inSeconds % 60}s'),
            _statRow('Hand coverage', '${(cov * 100).toStringAsFixed(1)}%'),
            _statRow('Task labels', '${_activeTasks.length}'),
            const SizedBox(height: 32),
            // Upload button
            FilledButton.icon(
              onPressed: _uploading ? null : _upload,
              icon: _uploading
                  ? const SizedBox(
                      width: 18, height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.cloud_upload),
              label: Text(_uploading ? 'Uploading...' : 'Upload to EgoData'),
              style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(56)),
            ),
            if (_uploadStatus.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(_uploadStatus,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        color: _uploadStatus.startsWith('uploaded')
                            ? Colors.greenAccent
                            : Colors.orangeAccent)),
              ),
            const SizedBox(height: 24),
            // Worker rating
            const Text('How was this shift?', textAlign: TextAlign.center),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(5, (i) => IconButton(
                    icon: Icon(
                      i < _rating ? Icons.star : Icons.star_border,
                      color: Colors.amber,
                      size: 36,
                    ),
                    onPressed: () => setState(() => _rating = i + 1),
                  )),
            ),
            const SizedBox(height: 32),
            OutlinedButton(
              onPressed: () =>
                  Navigator.pushReplacementNamed(context, '/'),
              child: const Text('Start New Shift'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _statRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.white54)),
          Text(value,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        ],
      ),
    );
  }
}

// Stub — in full build this comes from the recording session
final List<String> _activeTasks = [];
