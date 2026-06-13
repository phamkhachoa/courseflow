import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/quiz_models.dart';

/// Quiz attempt flow:
///  - `GET  /v1/quizzes/{quizId}`                    sanitized student view
///  - `POST /v1/quizzes/{quizId}/attempts`           start (empty body)
///  - `POST /v1/quizzes/attempts/{attemptId}/submit` submit answers
///
/// Identity (studentId) is taken from the gateway-injected `X-User-Id` header,
/// so no self-identifying id is ever sent in a request body.
class QuizRepository {
  QuizRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<Quiz> getQuiz(String quizId) async {
    try {
      final res = await _dio.get<Object?>('/v1/quizzes/$quizId');
      return Quiz.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  /// Starts (or resumes) an attempt. Body is an empty `StartAttemptRequestDto`;
  /// the student is the authenticated caller.
  Future<QuizAttempt> startAttempt(String quizId) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/quizzes/$quizId/attempts',
        data: const <String, dynamic>{},
      );
      final body = ApiEnvelope.unwrapObject(res.data);
      final attempt = body['attempt'];
      return QuizAttempt.fromJson(
        attempt is Map<String, dynamic> ? attempt : body,
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  /// Submits the attempt. [answers] maps questionId -> the answer value the
  /// backend grades against (for single-choice that is the selected option's
  /// label). Mirrors `SubmitAttemptRequestDto{ answers: Map<questionId, json> }`.
  /// Returns the graded `QuizAttemptDto`.
  Future<QuizAttempt> submitAttempt({
    required String attemptId,
    required Map<String, String> answers,
  }) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/quizzes/attempts/$attemptId/submit',
        data: {'answers': answers},
      );
      return QuizAttempt.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final quizRepositoryProvider = Provider<QuizRepository>((ref) {
  return QuizRepository(ref.watch(dioClientProvider));
});

final quizProvider = FutureProvider.autoDispose.family<Quiz, String>((
  ref,
  quizId,
) {
  return ref.watch(quizRepositoryProvider).getQuiz(quizId);
});
