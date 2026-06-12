import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/async_value_view.dart';
import '../data/video_repository.dart';
import '../domain/video_models.dart';

/// Skeleton video screen. Renders metadata and playback URL.
/// Replace the placeholder player widget with video_player + Chewie or
/// media_kit for real HLS adaptive playback in production.
class VideoScreen extends ConsumerWidget {
  const VideoScreen({super.key, required this.videoId, this.userId = ''});

  final String videoId;
  final String userId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final video = ref.watch(videoProvider(videoId));
    final playback = ref.watch(playbackUrlProvider(videoId));
    final progress = userId.isNotEmpty
        ? ref.watch(videoProgressProvider((videoId: videoId, userId: userId)))
        : null;

    return Scaffold(
      appBar: AppBar(title: video.whenData((v) => Text(v.title)).valueOrNull ?? const Text('Video')),
      body: AsyncValueView<VideoAsset>(
        value: video,
        onRetry: () => ref.invalidate(videoProvider(videoId)),
        data: (v) => _VideoBody(
          video: v,
          playbackAsync: playback,
          progressAsync: progress,
          userId: userId,
          ref: ref,
        ),
      ),
    );
  }
}

class _VideoBody extends StatelessWidget {
  const _VideoBody({
    required this.video,
    required this.playbackAsync,
    required this.progressAsync,
    required this.userId,
    required this.ref,
  });

  final VideoAsset video;
  final AsyncValue<PlaybackUrl> playbackAsync;
  final AsyncValue<VideoProgress>? progressAsync;
  final String userId;
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    if (video.status != 'READY') {
      return Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.hourglass_top, size: 48, color: Colors.amber),
          const SizedBox(height: 12),
          Text('Video đang xử lý (${video.status})', style: Theme.of(context).textTheme.bodyLarge),
        ]),
      );
    }

    return ListView(
      children: [
        // Video player placeholder. Wire video_player / media_kit here.
        Container(
          height: 220,
          color: Colors.black,
          child: playbackAsync.when(
            loading: () => const Center(child: CircularProgressIndicator(color: Colors.white)),
            error: (e, _) => const Center(child: Icon(Icons.error, color: Colors.white)),
            data: (pb) => Stack(children: [
              const Center(child: Icon(Icons.play_circle_fill, size: 72, color: Colors.white70)),
              Positioned(
                bottom: 8, left: 12, right: 12,
                child: Text(
                  'URL: ${pb.url.length > 60 ? '${pb.url.substring(0, 60)}…' : pb.url}',
                  style: const TextStyle(color: Colors.white54, fontSize: 10),
                ),
              ),
            ]),
          ),
        ),

        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(video.title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text('${video.renditions.length} renditions · ${video.captions.length} phụ đề',
                style: Theme.of(context).textTheme.bodySmall),

            if (progressAsync != null) ...[
              const SizedBox(height: 12),
              progressAsync!.when(
                loading: () => const LinearProgressIndicator(),
                error: (_, __) => const SizedBox.shrink(),
                data: (p) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Tiến độ: ${p.positionSeconds}s / ${p.durationSeconds ?? '?'}s',
                      style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 4),
                  if (p.durationSeconds != null && p.durationSeconds! > 0)
                    LinearProgressIndicator(value: p.positionSeconds / p.durationSeconds!),
                  if (p.completed)
                    const Padding(
                      padding: EdgeInsets.only(top: 4),
                      child: Row(children: [
                        Icon(Icons.check_circle, color: Colors.green, size: 16),
                        SizedBox(width: 4),
                        Text('Đã hoàn thành', style: TextStyle(color: Colors.green)),
                      ]),
                    ),
                ]),
              ),
            ],

            if (video.captions.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text('Phụ đề', style: Theme.of(context).textTheme.titleSmall),
              Wrap(
                spacing: 8,
                children: video.captions
                    .map((c) => Chip(label: Text('${c.language.toUpperCase()} · ${c.kind}')))
                    .toList(),
              ),
            ],
          ]),
        ),
      ],
    );
  }
}
