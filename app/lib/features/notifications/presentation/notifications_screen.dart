import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/util/date_label.dart';
import '../../../core/widgets/async_value_view.dart';
import '../application/notifications_controller.dart';
import '../domain/notification_models.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(notificationsControllerProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: RefreshIndicator(
        onRefresh: () =>
            ref.refresh(notificationsControllerProvider.future),
        child: AsyncValueView<List<AppNotification>>(
          value: notifications,
          onRetry: () => ref.invalidate(notificationsControllerProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'You are all caught up.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final n = items[index];
              return ListTile(
                leading: Icon(
                  n.read
                      ? Icons.notifications_none
                      : Icons.notifications_active,
                  color: n.read
                      ? Theme.of(context).colorScheme.outline
                      : Theme.of(context).colorScheme.primary,
                ),
                title: Text(
                  n.title,
                  style: TextStyle(
                    fontWeight: n.read ? FontWeight.normal : FontWeight.w600,
                  ),
                ),
                subtitle: Text(
                  n.createdAt == null
                      ? n.body
                      : '${n.body}\n${n.createdAt!.label}',
                ),
                isThreeLine: n.createdAt != null,
                onTap: n.read
                    ? null
                    : () => ref
                        .read(notificationsControllerProvider.notifier)
                        .markRead(n.id),
              );
            },
          ),
        ),
      ),
    );
  }
}
