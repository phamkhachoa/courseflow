import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/widgets/async_value_view.dart';
import '../../media/data/media_repository.dart';
import '../../media/domain/media_models.dart';
import '../application/course_providers.dart';
import '../data/course_repository.dart';

/// Navigation payload for [ModuleDetailScreen], passed via go_router `extra`.
class ModuleArgs {
  const ModuleArgs({
    required this.courseId,
    required this.courseSlug,
    required this.title,
    required this.completed,
  });

  final String courseId;
  final String courseSlug;
  final String title;
  final bool completed;
}

/// Module content: lists media assets (video/doc/...) and lets the learner mark
/// the module complete. Marking complete refreshes the parent course detail so
/// the checkmark updates.
class ModuleDetailScreen extends ConsumerStatefulWidget {
  const ModuleDetailScreen({
    super.key,
    required this.courseId,
    required this.courseSlug,
    required this.moduleId,
    required this.title,
    required this.completed,
  });

  final String courseId;
  final String courseSlug;
  final String moduleId;
  final String title;
  final bool completed;

  @override
  ConsumerState<ModuleDetailScreen> createState() => _ModuleDetailScreenState();
}

class _ModuleDetailScreenState extends ConsumerState<ModuleDetailScreen> {
  late bool _completed = widget.completed;
  bool _updating = false;

  Future<void> _markComplete() async {
    setState(() => _updating = true);
    try {
      await ref.read(courseRepositoryProvider).markModuleProgress(
            courseId: widget.courseId,
            moduleId: widget.moduleId,
          );
      // Reflect the change on the course detail page.
      ref.invalidate(courseDetailProvider(widget.courseSlug));
      if (mounted) setState(() => _completed = true);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not update progress.')),
        );
      }
    } finally {
      if (mounted) setState(() => _updating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final media = ref.watch(moduleMediaProvider(widget.moduleId));
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: AsyncValueView<List<MediaAsset>>(
        value: media,
        onRetry: () => ref.invalidate(moduleMediaProvider(widget.moduleId)),
        isEmpty: (items) => items.isEmpty,
        emptyMessage: 'Module content is not available in the mobile app yet.',
        data: (assets) => ListView.separated(
          padding: const EdgeInsets.all(AppTheme.pagePadding),
          itemCount: assets.length,
          separatorBuilder: (_, __) => const SizedBox(height: AppTheme.gap),
          itemBuilder: (context, index) => _MediaTile(asset: assets[index]),
        ),
      ),
      bottomNavigationBar: SafeArea(
        minimum: const EdgeInsets.all(AppTheme.pagePadding),
        child: FilledButton.icon(
          onPressed: (_updating || _completed) ? null : _markComplete,
          icon: const Icon(Icons.check),
          label: Text(_completed ? 'Completed' : 'Mark complete'),
        ),
      ),
    );
  }
}

class _MediaTile extends StatelessWidget {
  const _MediaTile({required this.asset});

  final MediaAsset asset;

  IconData get _icon => switch (asset.kind) {
        MediaKind.video => Icons.play_circle_outline,
        MediaKind.document => Icons.description_outlined,
        MediaKind.audio => Icons.headphones_outlined,
        MediaKind.image => Icons.image_outlined,
        MediaKind.other => Icons.attachment_outlined,
      };

  String? get _subtitle {
    if (asset.durationSeconds <= 0) return null;
    final m = asset.durationSeconds ~/ 60;
    final s = asset.durationSeconds % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  Future<void> _open(BuildContext context) async {
    final uri = Uri.tryParse(asset.url);
    if (uri == null || asset.url.isEmpty) return;
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not open this resource.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(_icon),
        title: Text(asset.title),
        subtitle: _subtitle == null ? null : Text(_subtitle!),
        trailing: const Icon(Icons.open_in_new),
        onTap: () => _open(context),
      ),
    );
  }
}
