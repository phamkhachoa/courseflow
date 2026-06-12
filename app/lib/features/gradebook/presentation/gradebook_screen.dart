import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../../auth/application/auth_controller.dart';
import '../data/gradebook_repository.dart';
import '../domain/grade_models.dart';

/// Learner grade overview for a course, with rubric feedback per item.
class GradebookScreen extends ConsumerWidget {
  const GradebookScreen({super.key, required this.courseId});

  final String courseId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    if (user == null) {
      return const Scaffold(
        body: Center(child: Text('Sign in to view grades.')),
      );
    }
    final key = (courseId: courseId, studentId: user.id.toString());
    final grades = ref.watch(courseGradesProvider(key));
    return Scaffold(
      appBar: AppBar(title: const Text('Grades')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(courseGradesProvider(key).future),
        child: AsyncValueView<CourseGrades>(
          value: grades,
          onRetry: () => ref.invalidate(courseGradesProvider(key)),
          isEmpty: (g) => g.entries.isEmpty,
          emptyMessage: 'No graded work yet.',
          data: (g) => _GradesBody(grades: g),
        ),
      ),
    );
  }
}

class _GradesBody extends StatelessWidget {
  const _GradesBody({required this.grades});

  final CourseGrades grades;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(AppTheme.pagePadding),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('Overall', style: theme.textTheme.titleMedium),
                Text('${grades.overallPercent.toStringAsFixed(1)}%',
                    style: theme.textTheme.headlineSmall
                        ?.copyWith(color: theme.colorScheme.primary)),
              ],
            ),
          ),
        ),
        const SizedBox(height: AppTheme.gap),
        ...grades.entries.map((e) => _GradeTile(entry: e)),
      ],
    );
  }
}

class _GradeTile extends StatelessWidget {
  const _GradeTile({required this.entry});

  final GradeEntry entry;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: AppTheme.gap),
      child: ExpansionTile(
        shape: const Border(),
        title: Text(entry.title),
        subtitle: Text(
          entry.graded
              ? '${entry.score!.toStringAsFixed(0)} / ${entry.maxScore.toStringAsFixed(0)} · ${entry.percent.toStringAsFixed(0)}%'
              : 'Not graded',
          style: theme.textTheme.bodySmall?.copyWith(
            color: entry.graded
                ? theme.colorScheme.primary
                : theme.colorScheme.outline,
          ),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (entry.categoryName.isNotEmpty)
                    Text('Category: ${entry.categoryName}',
                        style: theme.textTheme.bodyMedium),
                  if (entry.letter.isNotEmpty)
                    Text('Letter: ${entry.letter}',
                        style: theme.textTheme.bodyMedium),
                  if (entry.isLate)
                    Text('Submitted late',
                        style: theme.textTheme.bodyMedium
                            ?.copyWith(color: theme.colorScheme.error)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
