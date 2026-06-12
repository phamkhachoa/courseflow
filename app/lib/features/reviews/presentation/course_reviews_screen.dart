import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../data/review_repository.dart';
import '../domain/review_models.dart';

class CourseReviewsScreen extends ConsumerWidget {
  const CourseReviewsScreen({super.key, required this.courseId});

  final String courseId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reviews = ref.watch(courseReviewsProvider(courseId));
    final summary = ref.watch(ratingSummaryProvider(courseId));
    return Scaffold(
      appBar: AppBar(title: const Text('Đánh giá')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showPostReviewSheet(context, ref),
        icon: const Icon(Icons.rate_review),
        label: const Text('Viết đánh giá'),
      ),
      body: Column(
        children: [
          summary.whenData((s) => _SummaryHeader(summary: s)).valueOrNull ?? const SizedBox.shrink(),
          Expanded(
            child: AsyncValueView<List<CourseReview>>(
              value: reviews,
              onRetry: () => ref.invalidate(courseReviewsProvider(courseId)),
              data: (list) {
                if (list.isEmpty) {
                  return const Center(child: Text('Chưa có đánh giá nào.'));
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(AppTheme.pagePadding),
                  itemCount: list.length,
                  separatorBuilder: (_, __) => const Divider(),
                  itemBuilder: (_, i) => _ReviewTile(review: list[i], courseId: courseId),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _showPostReviewSheet(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => _PostReviewSheet(courseId: courseId, ref: ref),
    );
  }
}

class _SummaryHeader extends StatelessWidget {
  const _SummaryHeader({required this.summary});

  final RatingSummary summary;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      child: Row(children: [
        Text(
          summary.averageRating.toStringAsFixed(1),
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _StarRow(rating: summary.averageRating.round()),
          Text('${summary.reviewCount} đánh giá', style: Theme.of(context).textTheme.bodySmall),
        ]),
      ]),
    );
  }
}

class _StarRow extends StatelessWidget {
  const _StarRow({required this.rating});

  final int rating;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(
        5,
        (i) => Icon(i < rating ? Icons.star : Icons.star_border, size: 16, color: Colors.amber),
      ),
    );
  }
}

class _ReviewTile extends ConsumerWidget {
  const _ReviewTile({required this.review, required this.courseId});

  final CourseReview review;
  final String courseId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          _StarRow(rating: review.rating),
          const Spacer(),
          Text(review.createdAt.substring(0, 10), style: Theme.of(context).textTheme.bodySmall),
        ]),
        if (review.title != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(review.title!, style: Theme.of(context).textTheme.titleSmall),
          ),
        if (review.body != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(review.body!),
          ),
        TextButton.icon(
          onPressed: () async {
            try {
              await ref.read(reviewRepositoryProvider).markHelpful(review.id, 'current-user');
              ref.invalidate(courseReviewsProvider(courseId));
            } catch (_) {}
          },
          icon: const Icon(Icons.thumb_up_outlined, size: 16),
          label: Text('Hữu ích (${review.helpfulCount})'),
        ),
      ]),
    );
  }
}

class _PostReviewSheet extends StatefulWidget {
  const _PostReviewSheet({required this.courseId, required this.ref});

  final String courseId;
  final WidgetRef ref;

  @override
  State<_PostReviewSheet> createState() => _PostReviewSheetState();
}

class _PostReviewSheetState extends State<_PostReviewSheet> {
  int _rating = 5;
  final _titleCtrl = TextEditingController();
  final _bodyCtrl = TextEditingController();
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 16, 16, bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text('Viết đánh giá', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(5, (i) => GestureDetector(
            onTap: () => setState(() => _rating = i + 1),
            child: Icon(i < _rating ? Icons.star : Icons.star_border, size: 32, color: Colors.amber),
          )),
        ),
        const SizedBox(height: 12),
        TextField(controller: _titleCtrl, decoration: const InputDecoration(labelText: 'Tiêu đề')),
        const SizedBox(height: 8),
        TextField(controller: _bodyCtrl, decoration: const InputDecoration(labelText: 'Nội dung'), maxLines: 3),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: _loading ? null : _submit,
          child: _loading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Gửi'),
        ),
      ]),
    );
  }

  Future<void> _submit() async {
    setState(() => _loading = true);
    try {
      await widget.ref.read(reviewRepositoryProvider).postReview(
            courseId: widget.courseId,
            userId: 'current-user',
            rating: _rating,
            title: _titleCtrl.text.trim().isEmpty ? null : _titleCtrl.text.trim(),
            body: _bodyCtrl.text.trim().isEmpty ? null : _bodyCtrl.text.trim(),
          );
      widget.ref.invalidate(courseReviewsProvider(widget.courseId));
      widget.ref.invalidate(ratingSummaryProvider(widget.courseId));
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Lỗi: $e')));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }
}
