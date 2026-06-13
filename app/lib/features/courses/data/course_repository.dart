import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/course_models.dart';

/// Course catalog + enrolled-course access.
///  - `GET /v1/courses`            public catalog (no auth)
///  - `GET /v1/courses/{slug}`     public course detail
///  - `GET /v1/enrollments?studentId=` enrolled course IDs (auth)
///  - `POST /v1/courses/{courseId}/modules/{moduleId}/progress`
class CourseRepository {
  CourseRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<CourseSummary>> publicCourses() async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/courses',
        options: Options(extra: {'skipAuth': true}),
      );
      return ApiEnvelope.unwrapList(res.data)
          .map(CourseSummary.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<CourseDetail> courseBySlug(String slug) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/courses/$slug',
        options: Options(extra: {'skipAuth': true}),
      );
      return CourseDetail.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<List<CourseSummary>> myCourses(String studentId) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/enrollments',
        queryParameters: {'studentId': studentId},
      );
      final enrolledCourseIds = ApiEnvelope.unwrapList(res.data)
          .where((row) {
            final status = (row['status'] as String? ?? '').toUpperCase();
            return status == 'ACTIVE' ||
                status == 'ENROLLED' ||
                status == 'COMPLETED';
          })
          .map((row) => row['courseId'])
          .whereType<String>()
          .toSet();
      if (enrolledCourseIds.isEmpty) return const [];

      final courses = await publicCourses();
      return courses
          .where((course) => enrolledCourseIds.contains(course.id))
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  /// Marks a module COMPLETED for the authenticated learner. Identity comes from
  /// the gateway and the endpoint always marks completion, so there is no body and
  /// no un-complete operation.
  Future<void> markModuleProgress({
    required String courseId,
    required String moduleId,
  }) async {
    try {
      await _dio.post<Object?>(
        '/v1/courses/$courseId/modules/$moduleId/progress',
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final courseRepositoryProvider = Provider<CourseRepository>((ref) {
  return CourseRepository(ref.watch(dioClientProvider));
});
