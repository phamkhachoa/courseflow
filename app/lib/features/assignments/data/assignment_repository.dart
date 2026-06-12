import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/assignment_models.dart';

/// Assignment APIs:
///  - `GET  /v1/assignments?courseId=`
///  - `POST /v1/assignments/{id}/submissions`
class AssignmentRepository {
  AssignmentRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<Assignment>> byCourse(String courseId) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/assignments',
        queryParameters: {'courseId': courseId},
      );
      return ApiEnvelope.unwrapList(res.data)
          .map(Assignment.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<void> submit({
    required String assignmentId,
    required String content,
  }) async {
    try {
      await _dio.post<Object?>(
        '/v1/assignments/$assignmentId/submissions',
        data: {'submissionText': content},
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final assignmentRepositoryProvider = Provider<AssignmentRepository>((ref) {
  return AssignmentRepository(ref.watch(dioClientProvider));
});

final assignmentsByCourseProvider = FutureProvider.autoDispose
    .family<List<Assignment>, String>((ref, courseId) {
      return ref.watch(assignmentRepositoryProvider).byCourse(courseId);
    });
