import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/auth_controller.dart';
import '../data/notification_repository.dart';
import '../domain/notification_models.dart';

/// Loads the signed-in user's notifications and supports optimistic mark-read.
class NotificationsController
    extends AutoDisposeAsyncNotifier<List<AppNotification>> {
  @override
  Future<List<AppNotification>> build() async {
    final user = ref.watch(authControllerProvider).user;
    if (user == null) return const [];
    return ref.watch(notificationRepositoryProvider).list(user.id.toString());
  }

  /// Marks one notification read, updating the UI immediately and rolling back
  /// if the server call fails.
  Future<void> markRead(String id) async {
    final current = state.valueOrNull;
    if (current == null) return;
    state = AsyncData([
      for (final n in current) n.id == id ? n.copyWith(read: true) : n,
    ]);
    try {
      await ref.read(notificationRepositoryProvider).markRead(id);
    } catch (_) {
      state = AsyncData(current); // rollback
    }
  }
}

final notificationsControllerProvider = AsyncNotifierProvider.autoDispose<
  NotificationsController,
  List<AppNotification>
>(NotificationsController.new);

/// Unread badge count derived from the loaded list.
final unreadCountProvider = Provider.autoDispose<int>((ref) {
  final list = ref.watch(notificationsControllerProvider).valueOrNull;
  return list?.where((n) => !n.read).length ?? 0;
});
