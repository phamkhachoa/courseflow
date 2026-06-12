import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../data/discussion_repository.dart';
import '../domain/discussion_models.dart';

class DiscussionListScreen extends ConsumerWidget {
  const DiscussionListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final threads = ref.watch(discussionThreadsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Discussions')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(discussionThreadsProvider.future),
        child: AsyncValueView<List<DiscussionThread>>(
          value: threads,
          onRetry: () => ref.invalidate(discussionThreadsProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'No discussions yet. Start one.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final t = items[index];
              return ListTile(
                title: Text(t.title),
                subtitle: Text('${t.authorName} · ${t.commentCount} comments'),
                trailing: const Icon(Icons.chevron_right),
              );
            },
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showNewThreadSheet(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('New thread'),
      ),
    );
  }

  Future<void> _showNewThreadSheet(BuildContext context, WidgetRef ref) {
    final titleCtrl = TextEditingController();
    final bodyCtrl = TextEditingController();
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppTheme.pagePadding),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleCtrl,
                decoration: const InputDecoration(labelText: 'Title'),
              ),
              const SizedBox(height: AppTheme.gap),
              TextField(
                controller: bodyCtrl,
                maxLines: 4,
                decoration: const InputDecoration(labelText: 'Message'),
              ),
              const SizedBox(height: AppTheme.gap),
              FilledButton(
                onPressed: () async {
                  await ref.read(discussionRepositoryProvider).createThread(
                        title: titleCtrl.text.trim(),
                        body: bodyCtrl.text.trim(),
                      );
                  ref.invalidate(discussionThreadsProvider);
                  if (context.mounted) Navigator.of(context).pop();
                },
                child: const Text('Post'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
