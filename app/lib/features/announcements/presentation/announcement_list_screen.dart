import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/util/date_label.dart';
import '../../../core/widgets/async_value_view.dart';
import '../data/announcement_repository.dart';
import '../domain/announcement_models.dart';

class AnnouncementListScreen extends ConsumerWidget {
  const AnnouncementListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final announcements = ref.watch(announcementsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Announcements')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(announcementsProvider.future),
        child: AsyncValueView<List<Announcement>>(
          value: announcements,
          onRetry: () => ref.invalidate(announcementsProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'No announcements yet.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: AppTheme.gap),
            itemBuilder: (context, index) =>
                _AnnouncementCard(announcement: items[index]),
          ),
        ),
      ),
    );
  }
}

class _AnnouncementCard extends StatelessWidget {
  const _AnnouncementCard({required this.announcement});

  final Announcement announcement;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(announcement.title, style: theme.textTheme.titleMedium),
            if (announcement.courseTitle.isNotEmpty ||
                announcement.publishedAt != null) ...[
              const SizedBox(height: 2),
              Text(
                [
                  if (announcement.courseTitle.isNotEmpty)
                    announcement.courseTitle,
                  if (announcement.publishedAt != null)
                    announcement.publishedAt!.label,
                ].join(' · '),
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.outline),
              ),
            ],
            const SizedBox(height: 8),
            Text(announcement.body, style: theme.textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}
