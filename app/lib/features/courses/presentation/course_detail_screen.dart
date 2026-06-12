import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../../enrollment/presentation/enroll_button.dart';
import '../application/course_providers.dart';
import '../domain/course_models.dart';
import 'module_detail_screen.dart';

class CourseDetailScreen extends ConsumerWidget {
  const CourseDetailScreen({super.key, required this.slug});

  final String slug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(courseDetailProvider(slug));
    return Scaffold(
      appBar: AppBar(title: const Text('Course')),
      body: AsyncValueView<CourseDetail>(
        value: detail,
        onRetry: () => ref.invalidate(courseDetailProvider(slug)),
        data: (course) => _Body(detail: course),
      ),
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({required this.detail});

  final CourseDetail detail;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final s = detail.summary;
    return ListView(
      padding: const EdgeInsets.all(AppTheme.pagePadding),
      children: [
        Row(
          children: [
            Chip(label: Text(s.code)),
            const SizedBox(width: 8),
            Text(s.level,
                style: theme.textTheme.labelMedium
                    ?.copyWith(color: theme.colorScheme.outline)),
          ],
        ),
        const SizedBox(height: AppTheme.gap),
        Text(s.title, style: theme.textTheme.headlineSmall),
        const SizedBox(height: AppTheme.gap),
        EnrollButton(courseId: s.id),
        const SizedBox(height: AppTheme.gap),
        Text(detail.description, style: theme.textTheme.bodyLarge),
        const SizedBox(height: 20),
        Wrap(
          spacing: AppTheme.gap,
          runSpacing: AppTheme.gap,
          children: [
            OutlinedButton.icon(
              onPressed: () => context.push('/courses/${s.id}/assignments'),
              icon: const Icon(Icons.assignment_outlined),
              label: const Text('Assignments'),
            ),
            OutlinedButton.icon(
              onPressed: () => context.push('/courses/${s.id}/grades'),
              icon: const Icon(Icons.grade_outlined),
              label: const Text('Grades'),
            ),
          ],
        ),
        if (detail.modules.isNotEmpty) ...[
          const SizedBox(height: 24),
          Text('Modules', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          ...detail.modules.map(
            (m) => ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                m.completed
                    ? Icons.check_circle
                    : Icons.radio_button_unchecked,
                color: m.completed ? theme.colorScheme.primary : null,
              ),
              title: Text(m.title),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.push(
                '/explore/${s.slug}/modules/${m.id}',
                extra: ModuleArgs(
                  courseId: s.id,
                  courseSlug: s.slug,
                  title: m.title,
                  completed: m.completed,
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}
