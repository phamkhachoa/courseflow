import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/util/date_label.dart';
import '../../../core/widgets/async_value_view.dart';
import '../data/deadline_repository.dart';
import '../domain/deadline_models.dart';

class DeadlineListScreen extends ConsumerWidget {
  const DeadlineListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final deadlines = ref.watch(dueDeadlinesProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Upcoming deadlines')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(dueDeadlinesProvider.future),
        child: AsyncValueView<List<DeadlineReminder>>(
          value: deadlines,
          onRetry: () => ref.invalidate(dueDeadlinesProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'No upcoming deadlines. Nicely done.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: AppTheme.gap),
            itemBuilder: (context, index) =>
                _DeadlineTile(reminder: items[index]),
          ),
        ),
      ),
    );
  }
}

class _DeadlineTile extends StatelessWidget {
  const _DeadlineTile({required this.reminder});

  final DeadlineReminder reminder;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final due = reminder.dueAt;
    final overdue = due != null && due.isBefore(DateTime.now());
    final accent =
        overdue ? theme.colorScheme.error : theme.colorScheme.primary;
    return Card(
      child: ListTile(
        leading: Icon(Icons.event_outlined, color: accent),
        title: Text(reminder.title),
        subtitle: Text(
          reminder.courseTitle.isEmpty
              ? (due?.label ?? 'No date')
              : '${reminder.courseTitle}\n${due?.label ?? 'No date'}',
        ),
        isThreeLine: reminder.courseTitle.isNotEmpty,
        trailing: due == null
            ? null
            : Text(
                due.dueLabel(),
                style: theme.textTheme.labelMedium?.copyWith(color: accent),
              ),
      ),
    );
  }
}
