import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/application/auth_controller.dart';

void main() {
  runApp(const ProviderScope(child: CourseFlowApp()));
}

class CourseFlowApp extends ConsumerStatefulWidget {
  const CourseFlowApp({super.key});

  @override
  ConsumerState<CourseFlowApp> createState() => _CourseFlowAppState();
}

class _CourseFlowAppState extends ConsumerState<CourseFlowApp> {
  @override
  void initState() {
    super.initState();
    // Restore any persisted session before the first frame settles; the router
    // shows a splash while status is `unknown`.
    Future.microtask(
      () => ref.read(authControllerProvider.notifier).bootstrap(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'CourseFlow',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      routerConfig: router,
    );
  }
}
