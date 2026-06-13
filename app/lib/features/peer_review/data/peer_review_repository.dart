import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/peer_review_models.dart';

/// Peer review APIs:
///  - `GET  /v1/peer-reviews/review-assignments/mine`       assigned queue
///  - `POST /v1/peer-reviews/review-assignments/{id}/submit`
class PeerReviewRepository {
  PeerReviewRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<PeerReviewAssignment>> queue() async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/peer-reviews/review-assignments/mine',
      );
      return ApiEnvelope.unwrapList(res.data)
          .map(PeerReviewAssignment.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<void> submitReview({
    required String reviewAssignmentId,
    required int score,
    required String comment,
  }) async {
    try {
      await _dio.post<Object?>(
        '/v1/peer-reviews/review-assignments/$reviewAssignmentId/submit',
        data: {'score': score, 'comment': comment},
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final peerReviewRepositoryProvider = Provider<PeerReviewRepository>((ref) {
  return PeerReviewRepository(ref.watch(dioClientProvider));
});

final peerReviewQueueProvider =
    FutureProvider.autoDispose<List<PeerReviewAssignment>>((ref) {
  return ref.watch(peerReviewRepositoryProvider).queue();
});
