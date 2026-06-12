import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/live_session_models.dart';

class LiveSessionRepository {
  LiveSessionRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<LiveSession>> listByCourse(String courseId) async {
    try {
      final res = await _dio.get<Object?>('/v1/live-sessions?courseId=$courseId');
      final list = ApiEnvelope.unwrapList(res.data);
      return list.map(LiveSession.fromJson).toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<Registration> register(String sessionId, String userId) async {
    try {
      final res = await _dio.post<Object?>(
        '/v1/live-sessions/$sessionId/register',
        data: {'userId': userId},
      );
      return Registration.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<JoinInfo> join(String sessionId, String userId) async {
    try {
      final res = await _dio.get<Object?>('/v1/live-sessions/$sessionId/join?userId=$userId');
      return JoinInfo.fromJson(ApiEnvelope.unwrapObject(res.data));
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final liveSessionRepositoryProvider = Provider<LiveSessionRepository>((ref) {
  return LiveSessionRepository(ref.watch(dioClientProvider));
});

final liveSessionsProvider = FutureProvider.autoDispose.family<List<LiveSession>, String>((
  ref,
  courseId,
) {
  return ref.watch(liveSessionRepositoryProvider).listByCourse(courseId);
});
