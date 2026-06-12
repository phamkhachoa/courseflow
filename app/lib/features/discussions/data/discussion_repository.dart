import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/discussion_models.dart';

/// Discussion APIs:
///  - `GET  /v1/discussions/threads`
///  - `POST /v1/discussions/threads`
///  - `GET  /v1/discussions/threads/{id}/comments`
///  - `POST /v1/discussions/threads/{id}/comments`
class DiscussionRepository {
  DiscussionRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<DiscussionThread>> threads() async {
    try {
      final res = await _dio.get<Object?>('/v1/discussions/threads');
      return ApiEnvelope.unwrapList(res.data)
          .map(DiscussionThread.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<void> createThread({
    required String title,
    required String body,
  }) async {
    try {
      await _dio.post<Object?>(
        '/v1/discussions/threads',
        data: {'title': title, 'body': body},
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<List<DiscussionComment>> comments(String threadId) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/discussions/threads/$threadId/comments',
      );
      return ApiEnvelope.unwrapList(res.data)
          .map(DiscussionComment.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<void> addComment({
    required String threadId,
    required String body,
  }) async {
    try {
      await _dio.post<Object?>(
        '/v1/discussions/threads/$threadId/comments',
        data: {'body': body},
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final discussionRepositoryProvider = Provider<DiscussionRepository>((ref) {
  return DiscussionRepository(ref.watch(dioClientProvider));
});

final discussionThreadsProvider =
    FutureProvider.autoDispose<List<DiscussionThread>>((ref) {
      return ref.watch(discussionRepositoryProvider).threads();
    });

final threadCommentsProvider = FutureProvider.autoDispose
    .family<List<DiscussionComment>, String>((ref, threadId) {
      return ref.watch(discussionRepositoryProvider).comments(threadId);
    });
