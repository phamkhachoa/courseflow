import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/grade_models.dart';

/// Gradebook read APIs:
///  - `GET /v1/gradebook/courses/{courseId}/students/{studentId}`
class GradebookRepository {
  GradebookRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<CourseGrades> studentGrades({
    required String courseId,
    required String studentId,
  }) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/gradebook/courses/$courseId/students/$studentId',
      );
      return CourseGrades.fromJson(ApiEnvelope.unwrap(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final gradebookRepositoryProvider = Provider<GradebookRepository>((ref) {
  return GradebookRepository(ref.watch(dioClientProvider));
});

/// (courseId, studentId) key for the grade query.
typedef GradeKey = ({String courseId, String studentId});

final courseGradesProvider = FutureProvider.autoDispose
    .family<CourseGrades, GradeKey>((ref, key) {
      return ref.watch(gradebookRepositoryProvider).studentGrades(
            courseId: key.courseId,
            studentId: key.studentId,
          );
    });
