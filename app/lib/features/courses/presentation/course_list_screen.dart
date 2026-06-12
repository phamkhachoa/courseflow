import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../application/course_providers.dart';
import '../domain/course_models.dart';

/// Public course catalog (discovery tab).
class CourseListScreen extends ConsumerWidget {
  const CourseListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final courses = ref.watch(publicCoursesProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Explore courses'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () => context.push('/search'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(publicCoursesProvider.future),
        child: AsyncValueView<List<CourseSummary>>(
          value: courses,
          onRetry: () => ref.invalidate(publicCoursesProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'No courses published yet.',
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

class CourseCard extends StatelessWidget {
  const CourseCard({super.key, required this.course});

  final CourseSummary course;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(AppTheme.radius),
        onTap: () => context.push('/explore/${course.slug}'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Chip(
                    label: Text(course.code),
                    visualDensity: VisualDensity.compact,
                  ),
                  const SizedBox(width: 8),
                  Text(course.level,
                      style: theme.textTheme.labelSmall
                          ?.copyWith(color: theme.colorScheme.outline)),
                ],
              ),
              const SizedBox(height: 8),
              Text(course.title, style: theme.textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                course.summary,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
