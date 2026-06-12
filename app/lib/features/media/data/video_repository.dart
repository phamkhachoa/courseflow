import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/video_models.dart';

class VideoRepository {
  VideoRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<VideoAsset> getVideo(String videoId) async {
    try {
      final res = await _dio.get<Object?>('/v1/media/videos/$videoId');
      return VideoAsset.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<PlaybackUrl> getPlaybackUrl(String videoId, {String protocol = 'hls'}) async {
    try {
      final res = await _dio.get<Object?>('/v1/media/videos/$videoId/playback-url?protocol=$protocol');
      return PlaybackUrl.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<VideoProgress> getProgress(String videoId, String userId) async {
    try {
      final res = await _dio.get<Object?>('/v1/media/videos/$videoId/progress?userId=$userId');
      return VideoProgress.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<VideoProgress> saveProgress({
    required String videoId,
    required String userId,
    required int positionSeconds,
    int? durationSeconds,
    double playbackRate = 1.0,
    bool completed = false,
  }) async {
    try {
      final res = await _dio.put<Object?>(
        '/v1/media/videos/$videoId/progress',
        data: {
          'userId': userId,
          'positionSeconds': positionSeconds,
          if (durationSeconds != null) 'durationSeconds': durationSeconds,
          'playbackRate': playbackRate,
          'completed': completed,
        },
      );
      return VideoProgress.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final videoRepositoryProvider = Provider<VideoRepository>((ref) {
  return VideoRepository(ref.watch(dioClientProvider));
});

final videoProvider = FutureProvider.autoDispose.family<VideoAsset, String>((ref, videoId) {
  return ref.watch(videoRepositoryProvider).getVideo(videoId);
});

final playbackUrlProvider = FutureProvider.autoDispose.family<PlaybackUrl, String>((ref, videoId) {
  return ref.watch(videoRepositoryProvider).getPlaybackUrl(videoId);
});

final videoProgressProvider = FutureProvider.autoDispose.family<VideoProgress, ({String videoId, String userId})>((
  ref,
  args,
) {
  return ref.watch(videoRepositoryProvider).getProgress(args.videoId, args.userId);
});
