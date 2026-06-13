import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/util/date_label.dart';
import '../../../core/widgets/async_value_view.dart';
import '../data/peer_review_repository.dart';
import '../domain/peer_review_models.dart';

class PeerReviewQueueScreen extends ConsumerWidget {
  const PeerReviewQueueScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final queue = ref.watch(peerReviewQueueProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Peer review')),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(peerReviewQueueProvider.future),
        child: AsyncValueView<List<PeerReviewAssignment>>(
          value: queue,
          onRetry: () => ref.invalidate(peerReviewQueueProvider),
          isEmpty: (items) => items.isEmpty,
          emptyMessage: 'No reviews assigned right now.',
          data: (items) => ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: AppTheme.gap),
            itemBuilder: (context, index) => _ReviewCard(review: items[index]),
          ),
        ),
      ),
    );
  }
}

class _ReviewCard extends ConsumerWidget {
  const _ReviewCard({required this.review});

  final PeerReviewAssignment review;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(review.assignmentTitle,
                      style: theme.textTheme.titleMedium),
                ),
                if (review.submitted)
                  Icon(Icons.check_circle, color: theme.colorScheme.primary),
              ],
            ),
            if (review.dueAt != null)
              Text('Due ${review.dueAt!.dueLabel()}',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: theme.colorScheme.outline)),
            const SizedBox(height: 8),
            Text(review.submissionExcerpt,
                maxLines: 3, overflow: TextOverflow.ellipsis),
            if (!review.submitted) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonal(
                  onPressed: () => _showReviewSheet(context, ref),
                  child: const Text('Review'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _showReviewSheet(BuildContext context, WidgetRef ref) {
    final commentCtrl = TextEditingController();
    int score = 80;
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setSheetState) => Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Padding(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Score: $score / 100'),
                Slider(
                  value: score.toDouble(),
                  min: 0,
                  max: 100,
                  divisions: 20,
                  label: '$score',
                  onChanged: (v) => setSheetState(() => score = v.round()),
                ),
                TextField(
                  controller: commentCtrl,
                  maxLines: 4,
                  decoration: const InputDecoration(labelText: 'Feedback'),
                ),
                const SizedBox(height: AppTheme.gap),
                FilledButton(
                  onPressed: () async {
                    await ref.read(peerReviewRepositoryProvider).submitReview(
                          reviewAssignmentId: review.id,
                          score: score,
                          comment: commentCtrl.text.trim(),
                        );
                    ref.invalidate(peerReviewQueueProvider);
                    if (context.mounted) Navigator.of(context).pop();
                  },
                  child: const Text('Submit review'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
