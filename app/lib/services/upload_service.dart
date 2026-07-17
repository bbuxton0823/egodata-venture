/// Uploads captured video to the EgoData ingest API.
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class UploadService {
  final String baseUrl;
  final String? apiKey;

  UploadService({required this.baseUrl, this.apiKey});

  Map<String, String> get _headers => apiKey != null
      ? {'Authorization': 'Bearer $apiKey', 'Content-Type': 'application/json'}
      : {'Content-Type': 'application/json'};

  /// Get a presigned upload URL from the backend.
  Future<Map<String, dynamic>> requestUploadUrl(
      String workerId, String jobType, {String? homeId}) async {
    final r = await http.post(Uri.parse('$baseUrl/ingest/upload-url'),
        headers: _headers,
        body: jsonEncode(
            {'worker_id': workerId, 'job_type': jobType, 'home_id': homeId}));
    if (r.statusCode != 200) throw Exception('upload-url: ${r.body}');
    return jsonDecode(r.body);
  }

  /// Upload file to a presigned URL (S3/R2).
  Future<void> uploadToPresigned(String url, File file) async {
    final bytes = await file.readAsBytes();
    final r = await http.put(Uri.parse(url),
        headers: {'Content-Type': 'video/mp4'}, body: bytes);
    if (r.statusCode != 200) throw Exception('upload: ${r.statusCode}');
  }

  /// Confirm the upload so the backend queues processing.
  Future<Map<String, dynamic>> confirm(String key, String workerId,
      double durationS, {double? handCoverage}) async {
    final r = await http.post(Uri.parse('$baseUrl/ingest/confirm'),
        headers: _headers,
        body: jsonEncode({
          'key': key,
          'worker_id': workerId,
          'duration_s': durationS,
          'hand_coverage_est': handCoverage
        }));
    if (r.statusCode != 200) throw Exception('confirm: ${r.body}');
    return jsonDecode(r.body);
  }

  /// Direct upload (for MVP without S3 presigned).
  Future<Map<String, dynamic>> directUpload(
      File file, String workerId, String jobType) async {
    final request = http.MultipartRequest(
        'POST', Uri.parse('$baseUrl/ingest/direct'));
    request.headers.addAll(_headers);
    request.fields['worker_id'] = workerId;
    request.fields['job_type'] = jobType;
    request.files
        .add(await http.MultipartFile.fromPath('file', file.path));
    final r = await http.Response.fromStream(await request.send());
    if (r.statusCode != 200) throw Exception('direct-upload: ${r.body}');
    return jsonDecode(r.body);
  }
}
