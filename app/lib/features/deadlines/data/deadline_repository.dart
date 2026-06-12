import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../domain/deadline_models.dart';

/// Deadline APIs:
///  - `GET /v1/deadlines/reminders/due`  upcoming reminders for the user
class DeadlineRepository {
  DeadlineRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<DeadlineReminder>> due() async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/deadlines/reminders/due',
      );
      final items = ApiEnvelope.unwrapList(res.data)
          .map(DeadlineReminder.fromJson)
          .toList();
      // Soonest first; nulls last.
      items.sort((a, b) {
        if (a.dueAt == null) return 1;
        if (b.dueAt == null) return -1;
        return a.dueAt!.compareTo(b.dueAt!);
      });
      return items;
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final deadlineRepositoryProvider = Provider<DeadlineRepository>((ref) {
  return DeadlineRepository(ref.watch(dioClientProvider));
});

final dueDeadlinesProvider =
    FutureProvider.autoDispose<List<DeadlineReminder>>((ref) {
      return ref.watch(deadlineRepositoryProvider).due();
    });
