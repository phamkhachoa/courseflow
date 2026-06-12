import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/util/date_label.dart';
import '../../../core/widgets/async_value_view.dart';
import '../data/assignment_repository.dart';
import '../domain/assignment_models.dart';

/// Assignment list for a course. Pass the course id via the route.
class AssignmentListScreen extends ConsumerWidget {
  const AssignmentListScreen({super.key, required this.courseId});

  final String courseId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final provider = assignmentsByCourseProvider(courseId);
    final assignments = ref.watch(provider);
    return Scaffold(
      appBar: AppBar(title: const Text('Assignments')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(provider.future),
        child: AsyncValueView<List<Assignment>>(
          value: assignments,
          onRetry: () => ref.invalidate(provider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'No assignments for this course.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: AppTheme.gap),
            itemBuilder: (context, index) =>
                _AssignmentTile(assignment: items[index]),
          ),
        ),
      ),
    );
  }
}

class _AssignmentTile extends StatelessWidget {
  const _AssignmentTile({required this.assignment});

  final Assignment assignment;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final due = assignment.dueAt;
    final Color dueColor = assignment.isOverdue
        ? theme.colorScheme.error
        : theme.colorScheme.outline;
    return Card(
      child: ListTile(
        title: Text(assignment.title),
        subtitle: Text(
          due == null ? 'No due date' : '${due.label} · ${due.dueLabel()}',
          style: theme.textTheme.bodySmall?.copyWith(color: dueColor),
        ),
        trailing: const Icon(Icons.upload_file_outlined),
      ),
    );
  }
}
