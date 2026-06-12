import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../application/course_providers.dart';
import '../domain/course_models.dart';
import 'course_list_screen.dart';

/// Courses the signed-in learner is enrolled in (My courses tab).
class MyCoursesScreen extends ConsumerWidget {
  const MyCoursesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final courses = ref.watch(myCoursesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('My courses')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(myCoursesProvider.future),
        child: AsyncValueView<List<CourseSummary>>(
          value: courses,
          onRetry: () => ref.invalidate(myCoursesProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'You are not enrolled in any course yet.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: AppTheme.gap),
            itemBuilder: (context, index) =>
                CourseCard(course: items[index]),
          ),
        ),
      ),
    );
  }
}
