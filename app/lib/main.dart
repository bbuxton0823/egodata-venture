import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'screens/shift_start_screen.dart';
import 'screens/recording_screen.dart';
import 'screens/shift_end_screen.dart';
import 'services/session_provider.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: EgoDataApp()));
}

class EgoDataApp extends StatelessWidget {
  const EgoDataApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Data Hat',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF46DC64),
          brightness: Brightness.dark,
        ),
        scaffoldBackgroundColor: const Color(0xFF14181C),
      ),
      home: const ShiftStartScreen(),
      routes: {
        '/recording': (_) => const RecordingScreen(),
        '/shift-end': (_) => const ShiftEndScreen(),
      },
    );
  }
}
