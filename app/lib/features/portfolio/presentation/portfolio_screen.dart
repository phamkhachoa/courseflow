import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/util/date_label.dart';
import '../../../core/widgets/async_value_view.dart';
import '../../auth/application/auth_controller.dart';
import '../data/portfolio_repository.dart';
import '../domain/portfolio_models.dart';

class PortfolioScreen extends ConsumerWidget {
  const PortfolioScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final evidence = ref.watch(myEvidenceProvider);
    final user = ref.watch(authControllerProvider).user;
    return Scaffold(
      appBar: AppBar(title: const Text('Portfolio')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(myEvidenceProvider.future),
        child: AsyncValueView<List<PortfolioEvidence>>(
          value: evidence,
          onRetry: () => ref.invalidate(myEvidenceProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'Capture your first piece of evidence.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: AppTheme.gap),
            itemBuilder: (context, index) {
              final e = items[index];
              return Card(
                child: ListTile(
                  title: Text(e.title),
                  subtitle: Text(
                    e.createdAt == null
                        ? e.description
                        : '${e.description}\n${e.createdAt!.label}',
                  ),
                  isThreeLine: e.createdAt != null,
                  trailing: Chip(label: Text(e.tag)),
                ),
              );
            },
          ),
        ),
      ),
      floatingActionButton: user == null
          ? null
          : FloatingActionButton.extended(
              onPressed: () =>
                  _showAddSheet(context, ref, user.id.toString()),
              icon: const Icon(Icons.add),
              label: const Text('Add evidence'),
            ),
    );
  }

  Future<void> _showAddSheet(
    BuildContext context,
    WidgetRef ref,
    String studentId,
  ) {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
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
                controller: descCtrl,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Description'),
              ),
              const SizedBox(height: AppTheme.gap),
              FilledButton(
                onPressed: () async {
                  await ref.read(portfolioRepositoryProvider).addEvidence(
                        studentId: studentId,
                        title: titleCtrl.text.trim(),
                        description: descCtrl.text.trim(),
                        tag: 'GENERAL',
                      );
                  ref.invalidate(myEvidenceProvider);
                  if (context.mounted) Navigator.of(context).pop();
                },
                child: const Text('Save'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
