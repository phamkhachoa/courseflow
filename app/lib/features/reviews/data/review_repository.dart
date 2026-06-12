import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/review_models.dart';

class ReviewRepository {
  ReviewRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<CourseReview>> listByCourse(String courseId) async {
    try {
      final res = await _dio.get<Object?>('/v1/reviews/courses/$courseId');
      final list = ApiEnvelope.unwrapList(res.data);
      return list.map(CourseReview.fromJson).toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<RatingSummary> summary(String courseId) async {
    try {
      final res = await _dio.get<Object?>('/v1/reviews/courses/$courseId/summary');
      return RatingSummary.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<CourseReview> postReview({
    required String courseId,
    required String userId,
    required int rating,
    String? title,
    String? body,
  }) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/reviews',
        data: {
          'courseId': courseId,
          'userId': userId,
          'rating': rating,
          if (title != null) 'title': title,
          if (body != null) 'body': body,
        },
      );
      return CourseReview.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<CourseReview> markHelpful(String reviewId, String userId) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/reviews/$reviewId/helpful',
        data: {'userId': userId},
      );
      return CourseReview.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final reviewRepositoryProvider = Provider<ReviewRepository>((ref) {
  return ReviewRepository(ref.watch(dioClientProvider));
});

final courseReviewsProvider = FutureProvider.autoDispose.family<List<CourseReview>, String>((
  ref,
  courseId,
) {
  return ref.watch(reviewRepositoryProvider).listByCourse(courseId);
});

final ratingSummaryProvider = FutureProvider.autoDispose.family<RatingSummary, String>((
  ref,
  courseId,
) {
  return ref.watch(reviewRepositoryProvider).summary(courseId);
});
