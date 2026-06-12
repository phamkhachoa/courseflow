import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/notification_models.dart';

/// Notification APIs:
///  - `GET  /v1/notifications?userId=`
///  - `POST /v1/notifications/{id}/read`
///  - `POST /v1/notifications/preferences`
class NotificationRepository {
  NotificationRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<AppNotification>> list(String userId) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/notifications',
        queryParameters: {'userId': userId},
      );
      return ApiEnvelope.unwrapList(res.data)
          .map(AppNotification.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<void> markRead(String id) async {
    try {
      await _dio.post<Object?>('/v1/notifications/$id/read');
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }

  Future<void> updatePreferences(Map<String, bool> preferences) async {
    try {
      await _dio.post<Object?>(
        '/v1/notifications/preferences',
        data: preferences,
      );
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final notificationRepositoryProvider = Provider<NotificationRepository>((ref) {
  return NotificationRepository(ref.watch(dioClientProvider));
});
