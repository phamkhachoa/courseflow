import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_envelope.dart';
import '../../../core/api/dio_client.dart';
import '../../courses/domain/course_models.dart';

/// Public course search:
///  - `GET /v1/search/courses?q=`
///
/// Returns [CourseSummary] rows so results reuse the existing course card and
/// detail navigation.
class SearchRepository {
  SearchRepository(this._client);

  final DioClient _client;
  Dio get _dio => _client.dio;

  Future<List<CourseSummary>> courses(String query) async {
    try {
      final res = await _dio.get<Object?>(
        '/v1/search/courses',
        queryParameters: {'q': query},
        options: Options(extra: {'skipAuth': true}),
      );
      return ApiEnvelope.unwrapList(res.data)
          .map(CourseSummary.fromJson)
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiEnvelope.toApiException(e);
    }
  }
}

final searchRepositoryProvider = Provider<SearchRepository>((ref) {
  return SearchRepository(ref.watch(dioClientProvider));
});

/// Search results for a query. Empty query yields an empty list without a
/// network call.
final courseSearchProvider = FutureProvider.autoDispose
    .family<List<CourseSummary>, String>((ref, query) async {
      final trimmed = query.trim();
      if (trimmed.isEmpty) return const [];
      return ref.watch(searchRepositoryProvider).courses(trimmed);
    });
