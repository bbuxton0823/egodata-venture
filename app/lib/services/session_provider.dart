/// Session state shared across screens.
import 'package:flutter_riverpod/flutter_riverpod.dart';

class SessionState {
  final String workerId;
  final String jobType;
  final String? homeId;
  final bool isRecording;
  final Duration elapsed;
  final double? handCoverage;

  const SessionState({
    this.workerId = '',
    this.jobType = '',
    this.homeId,
    this.isRecording = false,
    this.elapsed = Duration.zero,
    this.handCoverage,
  });

  SessionState copyWith({
    String? workerId,
    String? jobType,
    String? homeId,
    bool? isRecording,
    Duration? elapsed,
    double? handCoverage,
  }) =>
      SessionState(
        workerId: workerId ?? this.workerId,
        jobType: jobType ?? this.jobType,
        homeId: homeId ?? this.homeId,
        isRecording: isRecording ?? this.isRecording,
        elapsed: elapsed ?? this.elapsed,
        handCoverage: handCoverage ?? this.handCoverage,
      );
}

class SessionNotifier extends StateNotifier<SessionState> {
  SessionNotifier() : super(const SessionState());

  void start(String workerId, String jobType, {String? homeId}) {
    state = state.copyWith(
        workerId: workerId, jobType: jobType, homeId: homeId,
        isRecording: true, elapsed: Duration.zero);
  }

  void tick(Duration elapsed) {
    state = state.copyWith(elapsed: elapsed);
  }

  void updateHandCoverage(double cov) {
    state = state.copyWith(handCoverage: cov);
  }

  void stop() {
    state = state.copyWith(isRecording: false);
  }
}

final sessionProvider = StateNotifierProvider<SessionNotifier, SessionState>(
    (_) => SessionNotifier());
