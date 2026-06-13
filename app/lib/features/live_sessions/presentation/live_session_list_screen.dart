import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../data/live_session_repository.dart';
import '../domain/live_session_models.dart';

class LiveSessionListScreen extends ConsumerWidget {
  const LiveSessionListScreen({super.key, required this.courseId});

  final String courseId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sessions = ref.watch(liveSessionsProvider(courseId));
    return Scaffold(
      appBar: AppBar(title: const Text('Lớp trực tuyến')),
      body: AsyncValueView<List<LiveSession>>(
        value: sessions,
        onRetry: () => ref.invalidate(liveSessionsProvider(courseId)),
        data: (list) {
          if (list.isEmpty) {
            return const Center(child: Text('Chưa có buổi live nào được lên lịch.'));
          }
          return ListView.separated(
            padding: const EdgeInsets.all(AppTheme.pagePadding),
            itemCount: list.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, i) => _SessionCard(session: list[i], courseId: courseId),
          );
        },
      ),
    );
  }
}

class _SessionCard extends ConsumerWidget {
  const _SessionCard({required this.session, required this.courseId});

  final LiveSession session;
  final String courseId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isLive = session.status == 'LIVE';
    final isScheduled = session.status == 'SCHEDULED';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Expanded(child: Text(session.title, style: Theme.of(context).textTheme.titleMedium)),
              _StatusBadge(status: session.status),
            ]),
            if (session.description != null) ...[
              const SizedBox(height: 4),
              Text(session.description!, style: Theme.of(context).textTheme.bodySmall),
            ],
            const SizedBox(height: 8),
            Text('Bắt đầu: ${session.scheduledStart}', style: Theme.of(context).textTheme.bodySmall),
            if (session.capacity != null)
              Text('Sức chứa: ${session.capacity}', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 12),
            Row(children: [
              if (isScheduled)
                FilledButton(
                  onPressed: () => _register(context, ref),
                  child: const Text('Đăng ký'),
                ),
              if (isLive) ...[
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: () => _join(context, ref),
                  child: const Text('Tham gia ngay'),
                ),
              ],
            ]),
          ],
        ),
      ),
    );
  }

  Future<void> _register(BuildContext context, WidgetRef ref) async {
    // userId should come from auth state; placeholder here
    const userId = 'current-user';
    try {
      await ref.read(liveSessionRepositoryProvider).register(session.id, userId);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Đã đăng ký thành công!')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Lỗi: $e')));
      }
    }
  }

  Future<void> _join(BuildContext context, WidgetRef ref) async {
    const userId = 'current-user';
    try {
      final info = await ref.read(liveSessionRepositoryProvider).join(session.id, userId);
      final uri = Uri.tryParse(info.joinUrl);
      if (uri != null && await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Lỗi: $e')));
      }
    }
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      'LIVE' => Colors.green,
      'ENDED' || 'CANCELLED' => Colors.grey,
      _ => Colors.blue,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
      child: Text(status, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}
