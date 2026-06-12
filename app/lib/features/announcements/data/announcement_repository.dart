import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/announcement_models.dart';

/// Announcement APIs (learner sees published announcements):
///  - `GET /v1/announcements`
class AnnouncementRepository {
  AnnouncementRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<Announcement>> list() async {
    try {
      final res = await _dio.get<Object?>('/v1/announcements');
      final items = ApiEnvelope.unwrapList(res.data)
          .map(Announcement.fromJson)
          .toList();
      // Newest first; nulls last.
      items.sort((a, b) {
        if (a.publishedAt == null) return 1;
        if (b.publishedAt == null) return -1;
        return b.publishedAt!.compareTo(a.publishedAt!);
      });
      return items;
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final announcementRepositoryProvider = Provider<AnnouncementRepository>((ref) {
  return AnnouncementRepository(ref.watch(dioClientProvider));
});

final announcementsProvider =
    FutureProvider.autoDispose<List<Announcement>>((ref) {
      return ref.watch(announcementRepositoryProvider).list();
    });
