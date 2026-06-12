import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/enrollment_models.dart';

/// Enrollment APIs:
///  - `GET  /v1/enrollments?courseId=&studentId=`  current status
///  - `POST /v1/enrollments`                        enroll
///  - `POST /v1/waitlist`                           join waitlist
class EnrollmentRepository {
  EnrollmentRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<Enrollment> status({
    required String courseId,
    required String studentId,
  }) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/enrollments',
        queryParameters: {'courseId': courseId, 'studentId': studentId},
      );
      final rows = ApiEnvelope.unwrapList(res.data);
      if (rows.isEmpty) return const Enrollment.notEnrolled();
      return Enrollment.fromJson(rows.first);
    } on DioException catch (e) {
      final mapped = ApiEnvelope.toApiException(e);
      // No enrollment record yet is a normal "not enrolled" state.
      if (mapped.isNotFound) return const Enrollment.notEnrolled();
      throw mapped;
    }
  }

  Future<Enrollment> enroll(String courseId) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/enrollments',
        data: {'courseId': courseId},
      );
      return Enrollment.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<Enrollment> joinWaitlist(String courseId) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/waitlist',
        data: {'courseId': courseId},
      );
      return Enrollment.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final enrollmentRepositoryProvider = Provider<EnrollmentRepository>((ref) {
  return EnrollmentRepository(ref.watch(dioClientProvider));
});
